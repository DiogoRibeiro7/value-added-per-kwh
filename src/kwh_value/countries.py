"""Electricity use and income across countries, from Our World in Data's energy dataset.

* ``country_panel``: one row per country for the chosen year, with GDP per capita (purchasing
  power parity, the Maddison Project series OWID carries), electricity demand per capita and GDP
  per kWh. Aggregates and very small countries are dropped.
* ``floor``: for each income threshold, the lowest electricity use among the countries above it.
  This is the claim behind the chart that circulated ("no rich country uses less than ...").
* ``residuals``: a log-log line through the cloud. A country far above it uses much more
  electricity than countries of its income; one far below uses much less.
* ``smelters``: for countries with a known primary aluminium output, the share of their
  electricity that smelting takes at a typical consumption per tonne. Aluminium is the cleanest
  case of an industry whose electricity use says little about the income it brings.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def country_panel(cfg, owid: pd.DataFrame) -> pd.DataFrame:
    c = cfg.raw["countries"]
    d = owid[(owid["year"] == int(c["year"])) & owid["iso_code"].notna()].copy()
    d = d[~d["iso_code"].astype(str).str.startswith("OWID")]
    d["gdp_per_capita"] = d["gdp"] / d["population"]
    d = d.rename(columns={"electricity_demand_per_capita": "kwh_per_capita"})
    d = d.dropna(subset=["gdp_per_capita", "kwh_per_capita"])
    d = d[(d["population"] >= float(c["min_population"])) & (d["kwh_per_capita"] > 0)]
    d["gdp_per_kwh"] = d["gdp_per_capita"] / d["kwh_per_capita"]
    cols = [
        "country",
        "iso_code",
        "year",
        "population",
        "gdp_per_capita",
        "kwh_per_capita",
        "gdp_per_kwh",
        "electricity_demand",
    ]
    return d[cols].sort_values("gdp_per_capita").reset_index(drop=True)


def floor(cfg, panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for threshold in cfg.raw["countries"]["income_thresholds"]:
        rich = panel[panel["gdp_per_capita"] >= threshold]
        lowest = rich.nsmallest(1, "kwh_per_capita").iloc[0]
        rows.append(
            {
                "gdp_per_capita_at_least": threshold,
                "countries": len(rich),
                "lowest_kwh_per_capita": lowest["kwh_per_capita"],
                "country_with_lowest": lowest["country"],
            }
        )
    return pd.DataFrame(rows)


def fit(panel: pd.DataFrame) -> dict:
    """OLS of log electricity per capita on log GDP per capita."""
    x, y = np.log(panel["gdp_per_capita"]), np.log(panel["kwh_per_capita"])
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (intercept + slope * x)
    r2 = 1 - (resid**2).sum() / ((y - y.mean()) ** 2).sum()
    return {
        "countries": len(panel),
        "slope": slope,
        "intercept": intercept,
        "r2": r2,
        "residual_sd": resid.std(),
    }


def residuals(panel: pd.DataFrame) -> pd.DataFrame:
    f = fit(panel)
    out = panel.copy()
    predicted = f["intercept"] + f["slope"] * np.log(out["gdp_per_capita"])
    out["log_residual"] = np.log(out["kwh_per_capita"]) - predicted
    out["ratio_to_line"] = np.exp(out["log_residual"])  # electricity use relative to the line
    return out.sort_values("log_residual", ascending=False).reset_index(drop=True)


def smelters(cfg, panel: pd.DataFrame) -> pd.DataFrame:
    a = cfg.raw["countries"]["aluminium"]
    mwh_per_t = float(a["mwh_per_tonne"])
    rows = []
    res = residuals(panel).set_index("country")
    for country, item in a["production_kt"].items():
        if country not in res.index:
            continue
        twh = item["kt"] * mwh_per_t / 1e3  # kt * MWh/t = GWh; / 1e3 = TWh
        demand = res.loc[country, "electricity_demand"]
        rows.append(
            {
                "country": country,
                "aluminium_kt": item["kt"],
                "aluminium_year": item["year"],
                "smelting_twh": twh,
                "electricity_demand_twh": demand,
                "smelting_share": twh / demand,
                "ratio_to_line": res.loc[country, "ratio_to_line"],
                "source": item["source"],
            }
        )
    cols = [
        "country",
        "aluminium_kt",
        "aluminium_year",
        "smelting_twh",
        "electricity_demand_twh",
        "smelting_share",
        "ratio_to_line",
        "source",
    ]
    out = pd.DataFrame(rows, columns=cols)
    return out.sort_values("smelting_share", ascending=False).reset_index(drop=True)


def run(cfg, owid: pd.DataFrame) -> dict[str, pd.DataFrame]:
    panel = country_panel(cfg, owid)
    tables = {
        "country_panel": residuals(panel),
        "country_floor": floor(cfg, panel),
        "country_fit": pd.DataFrame([fit(panel)]),
        "country_smelters": smelters(cfg, panel),
    }
    for name, df in tables.items():
        df.to_csv(cfg.tables / f"{name}.csv", index=False)
    return tables
