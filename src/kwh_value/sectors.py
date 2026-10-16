"""Gross value added per kWh of electricity by sector, from energy balances and national accounts.

Electricity comes from Eurostat's energy balance (final consumption, energy use, by sector) and
value added from the national accounts by industry (NACE Rev. 2, current prices). The two use
different classifications, so each sector of the balance is matched to the NACE divisions it
covers (``config/default.yaml``). Some sectors are left out: households (no value added),
transport (whose energy is mostly fuel, so value added per kWh of electricity says nothing about
it) and the energy industries (their electricity is not final consumption).

For the sectors kept, the economy's value added per kWh is a weighted mean of the sectors':

    VA / E = sum_i (E_i / E) * (VA_i / E_i),

with each sector weighted by its share of the electricity. Moving electricity between sectors
moves the mean even when no sector changes.
"""

from __future__ import annotations

import pandas as pd


def _values(df: pd.DataFrame, code_col: str) -> pd.DataFrame:
    """Geo by code, one period."""
    return df.pivot_table(index=code_col, columns="geo", values="value", aggfunc="sum")


def table(cfg, inputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per country and sector: electricity, value added, value added per kWh, shares."""
    s = cfg.raw["sectors"]
    elec = _values(inputs["electricity"], "nrg_bal")
    va = _values(inputs["value_added"], "nace_r2")
    rows = []
    for geo in s["geos"]:
        for name, m in s["mapping"].items():
            gwh = float(elec.loc[m["energy"], geo].sum())
            meur = float(va.loc[m["nace"], geo].sum() - va.loc[m.get("minus", []), geo].sum())
            rows.append(
                {
                    "geo": geo,
                    "sector": name,
                    "group": m["group"],
                    "gwh": gwh,
                    "va_meur": meur,
                    "eur_per_kwh": meur / gwh if gwh else float("nan"),
                }
            )
    out = pd.DataFrame(rows)
    covered = out.groupby("geo")[["gwh", "va_meur"]].transform("sum")
    out["share_of_covered_electricity"] = out["gwh"] / covered["gwh"]
    out["share_of_covered_va"] = out["va_meur"] / covered["va_meur"]
    final = elec.loc["FC_E"]
    out["share_of_final_electricity"] = out["gwh"] / out["geo"].map(final)
    return out


def economy(cfg, inputs: dict[str, pd.DataFrame], sectors: pd.DataFrame) -> pd.DataFrame:
    """Economy-wide ratios, and the check that the covered sectors' weighted mean is exact."""
    s = cfg.raw["sectors"]
    elec = _values(inputs["electricity"], "nrg_bal")
    va = _values(inputs["value_added"], "nace_r2")
    gdp = _values(inputs["gdp"], "na_item").loc["B1GQ"]
    rows = []
    for geo in s["geos"]:
        sub = sectors[sectors["geo"] == geo]
        weighted = (sub["share_of_covered_electricity"] * sub["eur_per_kwh"]).sum()
        fc, hh = elec.loc["FC_E", geo], elec.loc["FC_OTH_HH_E", geo]
        rows.append(
            {
                "geo": geo,
                "year": int(s["year"]),
                "final_electricity_gwh": fc,
                "households_gwh": hh,
                "gdp_meur": gdp[geo],
                "gdp_per_kwh_final": gdp[geo] / fc,
                "gva_meur": va.loc["TOTAL", geo],
                "imputed_rents_meur": va.loc[s["imputed_rents"], geo],
                "gva_ex_rents_per_kwh_ex_households": (
                    va.loc["TOTAL", geo] - va.loc[s["imputed_rents"], geo]
                )
                / (fc - hh),
                "covered_gwh": sub["gwh"].sum(),
                "covered_share_of_final": sub["gwh"].sum() / fc,
                "covered_va_meur": sub["va_meur"].sum(),
                "covered_share_of_gva": sub["va_meur"].sum() / va.loc["TOTAL", geo],
                "covered_eur_per_kwh": sub["va_meur"].sum() / sub["gwh"].sum(),
                "weighted_mean_eur_per_kwh": weighted,
            }
        )
    return pd.DataFrame(rows)


def run(cfg, inputs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    sectors = table(cfg, inputs)
    tables = {"sector_value_added": sectors, "economy_value_added": economy(cfg, inputs, sectors)}
    for name, df in tables.items():
        df.to_csv(cfg.tables / f"{name}.csv", index=False)
    return tables
