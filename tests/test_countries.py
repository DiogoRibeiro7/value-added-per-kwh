"""The cross-country panel, the income floor, the log-log fit and smelter shares."""

import numpy as np
import pandas as pd
import pytest

from kwh_value import countries


def synthetic_owid(year: int = 2022) -> pd.DataFrame:
    """Countries on an exact line kWh = 0.02 * GDP^1.2, plus one far above it and noise rows."""
    rng = np.random.default_rng(1)
    gdp_pc = np.geomspace(800, 90000, 40)
    rows = [
        {
            "country": f"C{i}",
            "iso_code": f"C{i:02d}",
            "year": year,
            "population": 5e6,
            "gdp": g * 5e6,
            "electricity_demand_per_capita": 0.02 * g**1.2,
            "electricity_demand": 0.02 * g**1.2 * 5e6 / 1e9,
        }
        for i, g in enumerate(gdp_pc)
    ]
    rows.append(
        {
            "country": "Smelterland",
            "iso_code": "SML",
            "year": year,
            "population": 4e5,
            "gdp": 40000 * 4e5,
            "electricity_demand_per_capita": 50000.0,
            "electricity_demand": 50000.0 * 4e5 / 1e9,
        }
    )
    rows += [
        {
            "country": "World",
            "iso_code": "OWID_WRL",
            "year": year,
            "population": 8e9,
            "gdp": 1e14,
            "electricity_demand_per_capita": 3500.0,
            "electricity_demand": 28000.0,
        },
        {
            "country": "Tiny",
            "iso_code": "TNY",
            "year": year,
            "population": 5e4,
            "gdp": 1e9,
            "electricity_demand_per_capita": 900.0,
            "electricity_demand": 0.045,
        },
        {
            "country": "Old",
            "iso_code": "OLD",
            "year": year - 1,
            "population": 5e6,
            "gdp": 1e11,
            "electricity_demand_per_capita": 900.0,
            "electricity_demand": 4.5,
        },
    ]
    d = pd.DataFrame(rows)
    d.loc[rng.integers(0, 40), "gdp"] = np.nan  # one country without GDP is dropped
    return d


def test_panel_drops_aggregates_small_countries_other_years_and_gaps(cfg):
    p = countries.country_panel(cfg, synthetic_owid())
    assert "World" not in set(p["country"]) and "Tiny" not in set(p["country"])
    assert "Old" not in set(p["country"]) and len(p) == 40
    assert p["gdp_per_kwh"].to_numpy() == pytest.approx(
        (p["gdp_per_capita"] / p["kwh_per_capita"]).to_numpy()
    )


def test_fit_recovers_the_line_and_flags_the_outlier(cfg):
    p = countries.country_panel(cfg, synthetic_owid())
    on_line = p[p["country"] != "Smelterland"]
    f = countries.fit(on_line)
    assert f["slope"] == pytest.approx(1.2) and f["intercept"] == pytest.approx(np.log(0.02))
    assert f["r2"] == pytest.approx(1.0)
    r = countries.residuals(p)
    assert r.iloc[0]["country"] == "Smelterland" and r.iloc[0]["ratio_to_line"] > 5


def test_floor_reports_the_lowest_user_above_each_threshold(cfg):
    p = countries.country_panel(cfg, synthetic_owid())
    f = countries.floor(cfg, p).set_index("gdp_per_capita_at_least")
    for threshold, row in f.iterrows():
        rich = p[p["gdp_per_capita"] >= threshold]
        assert row["lowest_kwh_per_capita"] == pytest.approx(rich["kwh_per_capita"].min())
        assert row["countries"] == len(rich)


def test_smelter_share_is_output_times_intensity_over_demand(cfg):
    cfg.raw["countries"]["aluminium"]["production_kt"] = {
        "Smelterland": {"kt": 800, "year": 2022, "source": "test"},
        "Nowhere": {"kt": 100, "year": 2022, "source": "test"},  # not in the panel: skipped
    }
    p = countries.country_panel(cfg, synthetic_owid())
    s = countries.smelters(cfg, p)
    assert list(s["country"]) == ["Smelterland"]
    twh = 800 * cfg.raw["countries"]["aluminium"]["mwh_per_tonne"] / 1e3
    assert s.iloc[0]["smelting_twh"] == pytest.approx(twh)
    assert s.iloc[0]["smelting_share"] == pytest.approx(twh / 20.0)
