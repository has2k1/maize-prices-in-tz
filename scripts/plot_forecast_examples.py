from datetime import date
from pathlib import Path

import polars as pl
from plotnine import (
    aes,
    annotate,
    arrow,
    element_blank,
    element_line,
    element_text,
    geom_line,
    geom_point,
    ggplot,
    labs,
    scale_x_continuous,
    scale_y_continuous,
    theme,
    theme_minimal,
)
from sklearn.linear_model import LinearRegression

from maize import forecast_pairs, maize_prices

INK = "#435052"
QUOTE = "#24495a"
FORECAST = "#884f14"
GRID = "#e0e5e7"

FORECAST_THEME = theme_minimal(base_size=12) + theme(
    figure_size=(8, 6),
    figure_format="retina",
    text=element_text(color=INK),
    axis_text=element_text(color=INK, size=11),
    axis_line=element_line(color=GRID, size=0.6),
    axis_ticks_major=element_line(color=INK, size=0.4),
    panel_grid=element_blank(),
)


def plot_baseline(may_price: float, june_price: float, output: Path) -> None:
    p = (
        ggplot()
        + annotate(
            "segment",
            x=0.02,
            xend=0.99,
            y=may_price,
            yend=may_price,
            color=FORECAST,
            linetype="dashed",
            arrow=arrow(length=0.10, type="closed"),
        )
        + annotate("point", x=[0, 1], y=[may_price, june_price], color=QUOTE, size=3)
        + annotate(
            "text",
            x=0,
            y=may_price + 1800,
            label=f"May quote\n{may_price:,.0f}",
            color=QUOTE,
            va="bottom",
            size=12,
        )
        + annotate(
            "text",
            x=1,
            y=may_price + 1800,
            label=f"June forecast\n{may_price:,.0f}",
            color=FORECAST,
            va="bottom",
            size=12,
        )
        + annotate(
            "text",
            x=0.95,
            y=june_price,
            label=f"June quote\n{june_price:,.0f}",
            color=QUOTE,
            ha="right",
            size=12,
        )
        + annotate(
            "errorbar",
            x=1.18,
            ymin=min(may_price, june_price),
            ymax=max(may_price, june_price),
            width=0.11,
            color=INK,
        )
        + annotate(
            "text",
            x=1.25,
            y=(may_price + june_price) / 2,
            label=f"Error\n{abs(may_price - june_price):,.0f}",
            color=INK,
            ha="left",
            size=12,
        )
        + scale_x_continuous(
            breaks=[0, 1],
            labels=["May 2026", "June 2026"],
            limits=(-0.28, 1.85),
            expand=(0, 0),
        )
        + scale_y_continuous(
            breaks=[40_000, 50_000, 60_000, 70_000, 80_000],
            labels=lambda values: [f"{value:,.0f}" for value in values],
            limits=(37_000, 89_000),
            expand=(0, 0),
        )
        + labs(y="Shillings per 100 kg")
        + FORECAST_THEME
        + theme(
            axis_title_x=element_blank(),
            panel_grid_major_y=element_line(color=GRID, size=0.5),
        )
    )
    p.save(output, verbose=False)


def plot_regression(train: pl.DataFrame, iringa: pl.DataFrame, output: Path) -> None:
    previous_prices = train.select("previous_price")
    model = LinearRegression().fit(previous_prices, train["price"])
    may_price = iringa["previous_price"].item()
    june_forecast = model.predict(iringa.select("previous_price")).item()
    prices = previous_prices["previous_price"]
    line = pl.DataFrame({"previous_price": [prices.min(), prices.max()]})
    line = line.with_columns(price=model.predict(line))

    p = (
        ggplot(train, aes("previous_price", "price"))
        + geom_point(color=QUOTE, alpha=0.35, size=2, stroke=0)
        + geom_line(data=line, color=QUOTE, size=0.9)
        + annotate(
            "point", x=27_000, y=143_000, color=QUOTE, alpha=0.35, size=2, stroke=0
        )
        + annotate(
            "segment",
            x=24_000,
            xend=30_000,
            y=135_000,
            yend=135_000,
            color=QUOTE,
            size=0.9,
        )
        + annotate(
            "text",
            x=33_000,
            y=[143_000, 135_000],
            label=["Earlier price pairs", "Fitted line"],
            color=INK,
            ha="left",
            size=12,
        )
        + annotate(
            "segment",
            x=[may_price, may_price],
            xend=[may_price, 20_000],
            y=[20_000, june_forecast],
            yend=[june_forecast, june_forecast],
            color=FORECAST,
            linetype="dashed",
            size=0.7,
        )
        + annotate(
            "point",
            x=may_price,
            y=june_forecast,
            fill=FORECAST,
            color="white",
            shape="o",
            size=3.2,
        )
        + scale_x_continuous(
            breaks=[25_000, 50_000, may_price, 100_000, 125_000, 150_000],
            labels=lambda values: [f"{value:,.0f}" for value in values],
            limits=(20_000, 151_500),
            expand=(0, 0),
        )
        + scale_y_continuous(
            breaks=[25_000, 50_000, june_forecast, 100_000, 125_000, 150_000],
            labels=lambda values: [f"{value:,.0f}" for value in values],
            limits=(20_000, 151_500),
            expand=(0, 0),
        )
        + labs(
            x="Previous month's price (shillings per 100 kg)",
            y="This month's price (shillings per 100 kg)",
        )
        + FORECAST_THEME
        + theme(
            axis_text=element_text(
                color=[INK, INK, FORECAST, INK, INK, INK],
                weight=["normal", "normal", "bold", "normal", "normal", "normal"],
            ),
        )
    )
    p.save(output, verbose=False)


def main() -> None:
    pairs = forecast_pairs(maize_prices())
    iringa = pairs.filter(market_id=85, month=date(2026, 6, 1))
    train = pairs.filter(pl.col("month") < date(2024, 1, 1))
    output = Path("figures")

    plot_baseline(
        iringa["previous_price"].item(),
        iringa["price"].item(),
        output / "iringa-baseline.png",
    )
    plot_regression(train, iringa, output / "iringa-regression.png")


if __name__ == "__main__":
    main()
