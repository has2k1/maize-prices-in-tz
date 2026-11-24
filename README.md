# Maize Prices in Tanzania

*Clean, visualise and interpret real market data with Python*

Learn how to manipulate data with [Polars](https://pola.rs/), plot it with [plotnine](https://plotnine.org/) and make tables with [great-tables](https://posit-dev.github.io/great-tables/) and forecast with [scikit-learn](https://scikit-learn.org/).

All exercises run in a modern browser.  · 

## Local preview

Install Make, uv and Quarto. Run this command from the repository root.

```sh
make preview
```

Open <http://127.0.0.1:25555/>. To build the site, run `make render`. Serve the resulting `_site/`.


## Data

The original World Food Programme (WFP) files are in `data/source/`. They contain 67,999 price quotes and a separate list of markets. Use the Parquet files for analysis. The workshop file has nine columns and covers four markets from January 2017 onwards. [Market quotes (Parquet)](data/market_quotes.parquet) · [Data dictionary](data/data-dict.yaml)

Run this command from the workshop root to rebuild the Parquet files. It checks the WFP price file, reads the sources and uses Polars 1.33.1 to select the workshop quotes.

```sh
make data
```

```sh
make validate-data
```

[Data Dictionary specification](https://data-dict.tidyverse.org/spec.html#source)

## Forecast figures

Regenerate the opening forecast chart and the two forecast examples from the repository root.

~~~sh
make figure
~~~

## Runtime

`uv run` installs the local Python packages listed in `pyproject.toml`. Each lesson lists the packages and files it needs in the browser under `pyodide`.

The workshop uses the `has2k1/live` extension and adapts the theme and **Show data** preview from the PyCon Africa workshop at revision `0f3cbf2`. Great Tables installs multimark from PyPI. [Quarto Live documentation](https://r-wasm.github.io/quarto-live/)

Use `#| preview: [sample, quotes]` in a Pyodide cell to offer a choice of dataframes under **Show data**. The first dataframe opens by default.
