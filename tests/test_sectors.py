"""Eurostat parsing, caching, and value added per kWh by sector."""

import pandas as pd
import pytest

from kwh_value import fetch, sectors
from tests.conftest import fake_eurostat

TSV = (
    "freq,unit,na_item,geo\\TIME_PERIOD\t2022 \t2023 \t2024 \n"
    "A,CP_MEUR,B1GQ,ES\t1375863.0 \t1496277.0 \t1598588.0 p\n"
    "A,CP_MEUR,B1GQ,PT\t243957.1 \t: \t291152.8 \n"
)


def test_read_tsv_splits_codes_values_and_flags():
    d = fetch.read_tsv(TSV)
    assert list(d.columns) == ["freq", "unit", "na_item", "geo", "time", "value", "flag"]
    es24 = d[(d["geo"] == "ES") & (d["time"] == "2024")].iloc[0]
    assert es24["value"] == pytest.approx(1598588.0) and es24["flag"] == "p"
    pt23 = d[(d["geo"] == "PT") & (d["time"] == "2023")].iloc[0]
    assert pd.isna(pt23["value"])  # ":" is not available
    assert len(d) == 6


def test_eurostat_queries_are_cached_by_url(cfg):
    calls = []
    first = fetch.eurostat_inputs(cfg, get=fake_eurostat(calls))
    assert len(calls) == 3
    assert any("nrg_bal_c/A." in u and ".E7000.GWH.PT+ES?" in u for u in calls)
    assert all("compressed=false" in u and "startPeriod=2023" in u for u in calls)
    again = fetch.eurostat_inputs(cfg, get=fake_eurostat(calls))
    assert len(calls) == 3  # read from the cache
    for name in first:
        assert again[name].equals(first[name])
    fetch.eurostat_inputs(cfg, get=fake_eurostat(calls), force=True)
    assert len(calls) == 6


def test_owid_download_is_checked_against_the_pinned_digest(cfg):
    with pytest.raises(ValueError, match="digest"):
        fetch.owid(cfg, get=lambda url: b"country,year\nX,2022\n")
    assert not (cfg.path("raw") / "owid-energy-data.csv").exists()


@pytest.fixture
def tables(cfg):
    return sectors.run(cfg, fetch.eurostat_inputs(cfg, get=fake_eurostat()))


def test_sector_values_for_2023(tables):
    t = tables["sector_value_added"].set_index(["geo", "sector"])
    # Spain, basic metals: NACE 24 value added over iron and steel plus non-ferrous electricity.
    assert t.loc[("ES", "Basic metals"), "gwh"] == pytest.approx(9880.7 + 3512.2)
    assert t.loc[("ES", "Basic metals"), "eur_per_kwh"] == pytest.approx(5099.0 / 13392.9)
    # Portugal, services: G to U and E and C33, less transport 49-51 and imputed rents.
    va = (
        54805.9
        + 11230.9
        + 16582.6
        + 24767.1
        + 22518.3
        + 42603.8
        + 6714.4
        + 2055.8
        + 1257.8
        - 5014.3
        - 235.1
        - 1304.7
        - 13363.9
    )
    assert t.loc[("PT", "Services"), "va_meur"] == pytest.approx(va)
    assert t.loc[("PT", "Services"), "eur_per_kwh"] == pytest.approx(va / 16657.477)
    shares = tables["sector_value_added"].groupby("geo")["share_of_covered_electricity"].sum()
    assert shares.to_numpy() == pytest.approx(1.0)


def test_economy_mean_is_the_electricity_weighted_mean_of_sectors(tables):
    e = tables["economy_value_added"].set_index("geo")
    assert e["weighted_mean_eur_per_kwh"].to_numpy() == pytest.approx(
        e["covered_eur_per_kwh"].to_numpy()
    )
    assert e.loc["ES", "gdp_per_kwh_final"] == pytest.approx(1496277.0 / 222672.96)
    assert e.loc["PT", "gva_ex_rents_per_kwh_ex_households"] == pytest.approx(
        (235589.3 - 13363.9) / (49539.735 - 14581.452)
    )
    assert (e["covered_share_of_final"] < 1).all() and (e["covered_share_of_gva"] < 1).all()


def test_every_mapped_code_is_requested_and_found(cfg, tables):
    t = tables["sector_value_added"]
    assert set(t["sector"]) == set(cfg.raw["sectors"]["mapping"])
    assert t["gwh"].gt(0).all() and t["va_meur"].gt(0).all()
