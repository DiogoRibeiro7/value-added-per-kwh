# value-added-per-kwh

How much economic output does a kWh of electricity produce, and how much does it depend on what
the kWh is used for? This repository measures it three ways, with open data:

* **across countries**: electricity demand per person against GDP per person (Our World in Data,
  2022), the lowest electricity use among countries above an income threshold, a log-log fit, and
  the share of each country's electricity that aluminium smelting takes;
* **by sector in Portugal and Spain**: gross value added per kWh of electricity for 14 sectors,
  matching Eurostat's energy balance to the national accounts by industry (2023);
* **for specific uses**: revenue and value added per kWh for green hydrogen, primary aluminium,
  battery-electric long-haul trucking and data centres, from sourced engineering and price data,
  with low, central and high cases.

A last step asks what a 100 MW grid connection adds to GDP under each use.

Value added (sales minus everything bought from other producers, electricity included) is the
quantity that adds up to GDP. Revenue per kWh is not comparable across uses, because it counts
the inputs again. See [`docs/methods.md`](docs/methods.md) for definitions, sources and limits.

## Run

```bash
pip install -e ".[dev]"
kwh-value all -v      # download, compute every table, draw the figures
pytest                # offline tests
```

Steps can be run one by one: `fetch`, `countries`, `sectors`, `uses`, `allocation`, `figures`.
Downloads are cached in `data/raw` (not committed): the OWID file is pinned to one commit and
checked against its digest, and each Eurostat query is kept as downloaded. The 2023 Eurostat
values behind the committed tables were first transcribed from Eurostat's tables (the same
values as `tests/data`); the **Reproduce** workflow (Actions tab, run on demand) downloads them
afresh, reruns everything and fails if the committed tables change.

## Outputs

`outputs/tables`:

| Table | Content |
|---|---|
| `country_panel` | GDP and electricity per person, GDP per kWh, ratio to the fitted line, by country |
| `country_floor` | lowest electricity use above each income threshold |
| `country_fit` | the log-log fit |
| `country_smelters` | aluminium smelting as a share of national electricity |
| `sector_value_added` | value added, electricity and value added per kWh by sector, PT and ES |
| `economy_value_added` | GDP per kWh and the identity check |
| `use_value_added` | revenue and value added per kWh by use and case |
| `allocation` | what a 100 MW connection adds under each use |

`outputs/figures`: `countries.png`, `sectors.png`, `uses.png`, each next to a CSV of the numbers
plotted.

## Data

* Our World in Data, [energy dataset](https://github.com/owid/energy-data) (CC BY 4.0), with
  electricity data from Ember and the Energy Institute and GDP from the Maddison Project Database.
* Eurostat, energy balances (`nrg_bal_c`) and national accounts (`nama_10_a64`, `nama_10_gdp`),
  through the [dissemination API](https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-introduction).
* Per-use parameters: sources listed next to each value in `config/default.yaml`.

## Citation

See [`CITATION.cff`](CITATION.cff).

## Licence

Apache 2.0.
