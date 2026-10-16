"""Revenue and value added per kWh for a few specific uses of electricity.

For each use the configuration gives the electricity per unit of output, the price of a unit, and
the other inputs bought per unit (raw materials, maintenance, tolls; everything that is not
labour, capital or electricity). Then, per kWh:

    revenue      = price / kWh per unit
    value added  = revenue - electricity price - other inputs / kWh per unit

Value added is what national accounts add up to GDP: sales minus everything bought from other
producers, the electricity included. It is the comparable quantity; revenue per kWh is not,
because it counts the value of the inputs again.

Every parameter is a central value with a low and a high one, so each result is a range. Prices
in dollars are converted at the configured exchange rate. ``break_even_eur_per_kwh`` is value
added before electricity: the electricity price at which a use's value added falls to zero.
"""

from __future__ import annotations

import pandas as pd

CASES = ("low", "central", "high")


def _eur(value: float, currency: str, usd_per_eur: float) -> float:
    if currency == "EUR":
        return value
    if currency == "USD":
        return value / usd_per_eur
    raise ValueError(f"unknown currency {currency}")


def _param(item: dict, key: str, case: str) -> float:
    p = item[key]
    if isinstance(p, dict):
        return float(p.get(case, p["central"]))
    return float(p)


def per_kwh(item: dict, case: str, usd_per_eur: float, price_eur_kwh: float) -> dict:
    """Revenue and value added per kWh (EUR) for one use and one case.

    The low case pairs the low price with the high electricity per unit and the high other
    inputs; the high case the reverse. The ranges are therefore wide on purpose.
    """
    opposite = {"low": "high", "central": "central", "high": "low"}[case]
    kwh = _param(item, "kwh_per_unit", opposite)
    price = _eur(_param(item, "price", case), item["currency"], usd_per_eur)
    other = _eur(_param(item, "other_inputs", opposite), item["currency"], usd_per_eur)
    passthrough = bool(item.get("electricity_passed_through", False))
    revenue = price / kwh + (price_eur_kwh if passthrough else 0.0)
    value_added = revenue - price_eur_kwh - other / kwh
    return {
        "revenue_eur_per_kwh": revenue,
        "value_added_eur_per_kwh": value_added,
        # Value added before paying for electricity: the electricity price at which value added
        # falls to zero, in EUR per kWh.
        "break_even_eur_per_kwh": value_added + price_eur_kwh,
        "kwh_per_unit": kwh,
        "price_eur_per_unit": price,
        "other_inputs_eur_per_unit": other,
    }


def table(cfg) -> pd.DataFrame:
    u = cfg.raw["uses"]
    usd_per_eur = float(u["usd_per_eur"])
    price = float(u["electricity_price_eur_mwh"]) / 1000
    rows = []
    for key, item in u["items"].items():
        for case in CASES:
            rows.append(
                {
                    "use": key,
                    "label": item["label"],
                    "case": case,
                    "unit": item["unit"],
                    **per_kwh(item, case, usd_per_eur, price),
                }
            )
    return pd.DataFrame(rows)


def run(cfg) -> dict[str, pd.DataFrame]:
    t = table(cfg)
    t.to_csv(cfg.tables / "use_value_added.csv", index=False)
    return {"use_value_added": t}
