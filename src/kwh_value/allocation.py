"""What one grid connection adds, depending on what it is used for.

A connection of ``mw`` megawatts is given to each use in turn, run for that use's typical hours
a year. The table gives the electricity it takes, the value added it produces (range from
``uses``), the value added per MW of connection, and what it does to the country's GDP per kWh.

The last column is a reminder about averages: a use can add value added and still lower the
economy's average per kWh, because its own value per kWh is below the average. What matters for
the decision is what the use adds, set against what the electricity and the connection could do
otherwise, not where it leaves the average.
"""

from __future__ import annotations

import pandas as pd


def table(cfg, uses: pd.DataFrame, economy: pd.DataFrame) -> pd.DataFrame:
    a = cfg.raw["allocation"]
    mw = float(a["mw"])
    rows = []
    for _, e in economy.iterrows():
        for _, u in uses.iterrows():
            hours = float(cfg.raw["uses"]["items"][u["use"]]["hours_per_year"])
            gwh = mw * hours / 1e3
            va = u["value_added_eur_per_kwh"] * gwh  # EUR/kWh * GWh = million EUR
            gdp, final = e["gdp_meur"], e["final_electricity_gwh"]
            rows.append(
                {
                    "geo": e["geo"],
                    "use": u["use"],
                    "label": u["label"],
                    "case": u["case"],
                    "mw": mw,
                    "hours_per_year": hours,
                    "gwh_per_year": gwh,
                    "share_of_final_electricity": gwh / final,
                    "value_added_meur": va,
                    "value_added_meur_per_mw": va / mw,
                    "share_of_gdp": va / gdp,
                    "gdp_per_kwh_before": gdp / final,
                    "gdp_per_kwh_after": (gdp + va) / (final + gwh),
                }
            )
    return pd.DataFrame(rows)


def run(cfg, uses: pd.DataFrame, economy: pd.DataFrame) -> dict[str, pd.DataFrame]:
    t = table(cfg, uses, economy)
    t.to_csv(cfg.tables / "allocation.csv", index=False)
    return {"allocation": t}
