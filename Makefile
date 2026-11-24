.PHONY: render preview data validate-data figure

render:
	uv run quarto render

preview:
	uv run quarto preview --no-browser

data:
	uv run python scripts/build_parquet.py

validate-data:
	uv run data-dict validate-data data/data-dict.yaml
	uv run data-dict validate-data drafts/data/data-dict.yaml

figure:
	uv run python scripts/plot_iringa_forecast.py
	uv run python -m scripts.plot_forecast_examples
