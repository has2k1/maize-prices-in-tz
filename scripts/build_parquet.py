import hashlib
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data = root / "data"
    draft_data = root / "drafts" / "data"
    source = data / "source" / "wfp_food_prices_tza.csv"
    source_sha256 = "55324dfa1923f73b7e795d18c1ed45496ca2bc4be4d3e6ac98d17472a49fd489"
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_sha256:
        raise SystemExit(f"Source checksum does not match the WFP snapshot: {source}")

    prices = pl.read_csv(source, try_parse_dates=True)
    market_quotes = prices.filter(
        pl.col("market_id").is_in([83, 85, 92, 2800]),
        pl.col("date") >= date(2017, 1, 1),
    ).select(
        "date",
        "market_id",
        "market",
        "commodity",
        "unit",
        "pricetype",
        "currency",
        "priceflag",
        "price",
    )
    tables = {
        data / "wfp_prices.parquet": prices,
        data / "market_registry.parquet": pl.read_csv(
            data / "source" / "wfp_markets_tza.csv"
        ),
        data / "market_quotes.parquet": market_quotes,
        draft_data / "zanzibar_retail.parquet": pl.read_csv(
            draft_data / "zanzibar-retail.csv", try_parse_dates=True
        ),
    }
    with TemporaryDirectory(dir=root) as directory:
        staging = Path(directory)
        for parquet, frame in tables.items():
            frame.write_parquet(staging / parquet.name, compression="zstd")
        for parquet, frame in tables.items():
            (staging / parquet.name).replace(parquet)
            print(f"Generated {parquet.relative_to(root)} ({frame.height:,} rows)")


if __name__ == "__main__":
    main()
