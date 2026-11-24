from pathlib import Path

import polars as pl
from pandas import Timedelta, date_range
from plotnine import (
    aes,
    annotate,
    element_blank,
    element_line,
    element_text,
    geom_hline,
    geom_line,
    geom_point,
    geom_vline,
    ggplot,
    labs,
    scale_x_datetime,
    scale_y_continuous,
    theme,
    theme_minimal,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    months = date_range("2025-12-01", "2026-06-01", freq="MS")
    june = months[-1]
    quotes = (
        pl.read_parquet(root / "data" / "market_quotes.parquet")
        .filter(
            pl.col("date").is_between(months[0].date(), june.date(), closed="left"),
            market_id=85,
            commodity="Maize",
            unit="100 KG",
            pricetype="Wholesale",
            currency="TZS",
            priceflag="actual",
        )
        .select(pl.col("date").dt.truncate("1mo").alias("month"), "price")
        .sort("month")
        .with_columns(
            line=(pl.col("month") != pl.col("month").shift().dt.offset_by("1mo"))
            .fill_null(True)
            .cum_sum()
        )
        .to_pandas()
    )
    may = quotes.iloc[-1]
    forecast_start = june - Timedelta(days=13)
    forecast_end = june + Timedelta(days=16)
    price_breaks = [50_000, 60_000, 70_000, 80_000]
    ink = "#435052"
    blue = "#24495A"
    amber = "#884f14"

    p = (
        ggplot(quotes, aes("month", "price"))
        + annotate(
            "rect",
            xmin=forecast_start,
            xmax=forecast_end,
            ymin=50_000,
            ymax=82_000,
            fill="#F8EFE0",
        )
        + geom_hline(yintercept=price_breaks, color="#e0e5e7", size=0.45)
        + geom_vline(xintercept=forecast_start, color="#c49b61", linetype="dashed", size=0.5)
        + geom_line(aes(group="line"), color=blue, size=1.15)
        + geom_point(color=blue, size=2.8)
        + annotate(
            "text",
            x=may["month"],
            y=may["price"] + 3_600,
            label=f"{may['price']:,.0f}",
            color=blue,
            size=12,
            fontweight="bold",
        )
        + annotate("text", x=june, y=65_000, label="?\nForecast", color=amber, size=14, fontweight="bold")
        + scale_x_datetime(
            breaks=months,
            labels=["Dec\n2025", "Jan\n2026", "Feb", "Mar", "Apr", "May", "Jun"],
            limits=(months[0] - Timedelta(days=7), forecast_end),
            expand=(0, 0),
        )
        + scale_y_continuous(
            breaks=price_breaks,
            labels=lambda values: [f"{value:,.0f}" for value in values],
            limits=(50_000, 82_000),
            expand=(0, 0),
        )
        + labs(title="Maize price per 100 kg")
        + theme_minimal(base_size=12)
        + theme(
            figure_size=(8, 5),
            figure_format="retina",
            panel_grid=element_blank(),
            axis_title=element_blank(),
            axis_line_x=element_line(color="#d2dadd", size=0.4),
            axis_text_x=element_text(
                color=[ink] * 6 + [amber],
                weight=["normal"] * 6 + ["bold"],
                size=11,
                margin={"t": 8},
            ),
            axis_text_y=element_text(color=ink),
            plot_title=element_text(color=ink, ha="left"),
            plot_title_position="plot",
        )
    )
    p.save(root / "figures" / "iringa-forecast.png")


if __name__ == "__main__":
    main()
