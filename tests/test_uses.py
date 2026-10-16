"""Revenue and value added per kWh by use, and what one grid connection adds."""

import copy

import pandas as pd
import pytest

from kwh_value import allocation, uses

ITEMS = {
    "widget": {
        "label": "Widget",
        "unit": "t",
        "currency": "USD",
        "kwh_per_unit": {"low": 10000, "central": 12000, "high": 15000},
        "price": {"low": 1800, "central": 2400, "high": 3000},
        "other_inputs": {"low": 600, "central": 900, "high": 1200},
        "hours_per_year": 8000,
    },
    "hosting": {
        "label": "Hosting",
        "unit": "kW-month",
        "currency": "EUR",
        "kwh_per_unit": 600,
        "price": 150,
        "other_inputs": 15,
        "electricity_passed_through": True,
        "hours_per_year": 6000,
    },
}


@pytest.fixture
def cfg_uses(cfg):
    cfg.raw["uses"]["items"] = copy.deepcopy(ITEMS)
    cfg.raw["uses"]["usd_per_eur"] = 1.25
    cfg.raw["uses"]["electricity_price_eur_mwh"] = 50.0
    return cfg


def test_per_kwh_formulas(cfg_uses):
    t = uses.table(cfg_uses).set_index(["use", "case"])
    w = t.loc[("widget", "central")]
    assert w["revenue_eur_per_kwh"] == pytest.approx(2400 / 1.25 / 12000)
    assert w["value_added_eur_per_kwh"] == pytest.approx((2400 - 900) / 1.25 / 12000 - 0.05)
    assert w["break_even_eur_per_kwh"] == pytest.approx((2400 - 900) / 1.25 / 12000)
    # Low case: low price, high electricity per unit, high other inputs.
    lo = t.loc[("widget", "low")]
    assert lo["revenue_eur_per_kwh"] == pytest.approx(1800 / 1.25 / 15000)
    assert lo["value_added_eur_per_kwh"] == pytest.approx((1800 - 1200) / 1.25 / 15000 - 0.05)
    # Electricity passed through at cost adds to revenue but not to value added.
    h = t.loc[("hosting", "central")]
    assert h["revenue_eur_per_kwh"] == pytest.approx(150 / 600 + 0.05)
    assert h["value_added_eur_per_kwh"] == pytest.approx((150 - 15) / 600)
    order = t.loc["widget", "value_added_eur_per_kwh"]
    assert order["low"] < order["central"] < order["high"]


def test_unknown_currency_is_refused(cfg_uses):
    cfg_uses.raw["uses"]["items"]["widget"]["currency"] = "GBP"
    with pytest.raises(ValueError, match="currency"):
        uses.table(cfg_uses)


def test_allocation_adds_value_added_and_moves_the_average(cfg_uses):
    u = uses.table(cfg_uses)
    economy = pd.DataFrame([{"geo": "PT", "gdp_meur": 270000.0, "final_electricity_gwh": 50000.0}])
    a = allocation.table(cfg_uses, u, economy).set_index(["use", "case"])
    w = a.loc[("widget", "central")]
    assert w["gwh_per_year"] == pytest.approx(100 * 8000 / 1e3)
    va = u.set_index(["use", "case"]).loc[("widget", "central"), "value_added_eur_per_kwh"]
    assert w["value_added_meur"] == pytest.approx(va * 800)
    assert w["value_added_meur_per_mw"] == pytest.approx(va * 8)
    assert w["gdp_per_kwh_after"] == pytest.approx((270000 + va * 800) / (50000 + 800))
    # A use below the average lowers the average while adding value added.
    assert w["value_added_meur"] > 0 and w["gdp_per_kwh_after"] < w["gdp_per_kwh_before"]
