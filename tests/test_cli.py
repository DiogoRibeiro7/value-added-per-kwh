"""The command line from download to figures, offline."""

import copy

import pandas as pd

from kwh_value import fetch
from kwh_value.cli import TABLES, main
from tests.conftest import fake_eurostat
from tests.test_countries import synthetic_owid
from tests.test_uses import ITEMS


def test_all_steps_write_every_table_and_figure(cfg, monkeypatch, capsys):
    cfg.raw["uses"]["items"] = copy.deepcopy(ITEMS)
    import yaml

    cfg.file.write_text(yaml.safe_dump(cfg.raw), encoding="utf-8")
    synthetic_owid().to_csv(cfg.path("raw") / "owid-energy-data.csv", index=False)  # cached
    monkeypatch.setattr(fetch, "_get", fake_eurostat())
    main(["all", "--config", str(cfg.file)])
    capsys.readouterr()
    for name in TABLES:
        assert (cfg.tables / f"{name}.csv").exists(), name
    figs = {p.stem for p in cfg.figures.glob("*.png")}
    assert figs == {"countries", "sectors", "uses"}
    for stem in figs:  # every figure comes with the numbers plotted
        assert len(pd.read_csv(cfg.figures / f"{stem}.csv"))
