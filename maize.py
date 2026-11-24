import pandas as pd
import polars as pl


def maize_prices() -> pl.DataFrame:
    return (
        pl.read_parquet("data/market_quotes.parquet", use_pyarrow=True)
        .filter(
            commodity="Maize",
            unit="100 KG",
            pricetype="Wholesale",
            currency="TZS",
            priceflag="actual",
        )
        .with_columns(month=pl.col("date").dt.truncate("1mo"))
        .select("market_id", "market", "month", "price")
        .sort("market_id", "month")
    )


def plot_data(prices: pl.DataFrame) -> pd.DataFrame:
    lines = (
        prices.with_columns(previous=pl.col("month").shift(1).over("market_id"))
        .with_columns(
            segment=(pl.col("month") != pl.col("previous").dt.offset_by("1mo"))
            .fill_null(True)
            .cum_sum()
            .over("market_id"),
        )
        .with_columns(line=pl.concat_str("market_id", "segment", separator="-"))
    )
    data = pd.DataFrame(lines.to_dict(as_series=False))
    data["month"] = pd.to_datetime(data["month"])
    return data


def months_in_span(first: pl.Expr, last: pl.Expr) -> pl.Expr:
    return (
        (last.dt.year() - first.dt.year()) * 12
        + last.dt.month().cast(pl.Int32)
        - first.dt.month().cast(pl.Int32)
        + 1
    )


def forecast_pairs(prices: pl.DataFrame) -> pl.DataFrame:
    previous = prices.select(
        "market_id",
        month=pl.col("month").dt.offset_by("1mo"),
        previous_price=pl.col("price"),
    )
    return (
        prices.filter(pl.col("market_id").is_in([85, 92, 2800]))
        .join(previous, on=["market_id", "month"], how="inner", validate="1:1")
        .sort("month", "market_id")
    )
