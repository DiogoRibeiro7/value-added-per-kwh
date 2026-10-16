"""Shared fixtures: a temporary copy of the configuration, and Eurostat responses rebuilt from the
2023 values in ``tests/data`` (see ``tests/data/README.md``)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest
import yaml

from kwh_value.config import load_config

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(__file__).parent / "data"


def eurostat_values() -> dict[str, pd.Series]:
    elec = pd.read_csv(DATA / "eurostat_nrg_bal_c_2023.csv").set_index(["nrg_bal", "geo"])["gwh"]
    va = pd.read_csv(DATA / "eurostat_nama_10_a64_2023.csv").set_index(["nace_r2", "geo"])["meur"]
    gdp = pd.read_csv(DATA / "eurostat_nama_10_gdp_2023.csv").set_index(["na_item", "geo"])["meur"]
    return {"nrg_bal_c": elec, "nama_10_a64": va, "nama_10_gdp": gdp}


def fake_eurostat(calls: list | None = None):
    """A stand-in for the HTTP GET that answers SDMX TSV queries from the fixture values."""
    values = eurostat_values()
    layout = {
        "nrg_bal_c": ("freq,nrg_bal,siec,unit,geo", 1, "A,{code},E7000,GWH,{geo}"),
        "nama_10_a64": ("freq,unit,nace_r2,na_item,geo", 2, "A,CP_MEUR,{code},B1G,{geo}"),
        "nama_10_gdp": ("freq,unit,na_item,geo", 2, "A,CP_MEUR,{code},{geo}"),
    }

    def get(url: str) -> bytes:
        if calls is not None:
            calls.append(url)
        dataset, key = re.search(r"/data/(\w+)/([^?]+)\?", url).groups()
        header, position, row = layout[dataset]
        parts = key.split(".")
        lines = [f"{header}\\TIME_PERIOD\t2023 "]
        for code in parts[position].split("+"):
            for geo in parts[-1].split("+"):
                v = values[dataset].get((code, geo))
                cell = ":" if v is None else f"{v} "
                lines.append(row.format(code=code, geo=geo) + f"\t{cell}")
        return ("\n".join(lines) + "\n").encode()

    return get


def write_config(tmp: Path, changes: dict | None = None):
    raw = yaml.safe_load((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    for key, value in (changes or {}).items():
        raw[key] = value
    (tmp / "config").mkdir(exist_ok=True)
    (tmp / "config" / "default.yaml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    return load_config(tmp / "config" / "default.yaml")


@pytest.fixture
def cfg(tmp_path):
    return write_config(tmp_path)
