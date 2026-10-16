"""Command line: kwh-value <step> or ``all``.

Steps: ``fetch`` (download and cache the data), ``countries``, ``sectors``, ``uses``,
``allocation`` and ``figures``. Each writes its tables to ``outputs/tables``; ``figures`` reads
them back. ``all`` runs every step in order.
"""

from __future__ import annotations

import argparse
import logging

import pandas as pd

from . import allocation, countries, fetch, figures, sectors, uses
from .config import DEFAULT_CONFIG, load_config

STEPS = ["fetch", "countries", "sectors", "uses", "allocation", "figures"]
TABLES = [
    "country_panel",
    "country_floor",
    "country_fit",
    "country_smelters",
    "sector_value_added",
    "economy_value_added",
    "use_value_added",
    "allocation",
]
log = logging.getLogger("kwh_value.cli")


def _read(cfg, name: str) -> pd.DataFrame | None:
    path = cfg.tables / f"{name}.csv"
    return pd.read_csv(path) if path.exists() else None


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="kwh-value", description=__doc__)
    parser.add_argument("command", choices=[*STEPS, "all"])
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--force", action="store_true", help="download again, ignoring the cache")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s"
    )
    cfg = load_config(args.config)
    cmd = args.command

    def wanted(step: str) -> bool:
        return cmd in (step, "all")

    if wanted("fetch"):
        fetch.owid(cfg, force=args.force)
        fetch.eurostat_inputs(cfg, force=args.force)
        print(f"cached in {cfg.path('raw')}")
    if wanted("countries"):
        t = countries.run(cfg, fetch.owid(cfg))
        print(t["country_floor"].to_string(index=False))
        print(t["country_fit"].round(3).to_string(index=False))
    if wanted("sectors"):
        t = sectors.run(cfg, fetch.eurostat_inputs(cfg))
        cols = ["geo", "sector", "gwh", "va_meur", "eur_per_kwh"]
        print(t["sector_value_added"][cols].round(2).to_string(index=False))
    if wanted("uses"):
        t = uses.run(cfg)["use_value_added"]
        print(t[t["case"] == "central"].round(3).to_string(index=False))
    if wanted("allocation"):
        use, economy = _read(cfg, "use_value_added"), _read(cfg, "economy_value_added")
        if use is None or economy is None:
            raise SystemExit("run `uses` and `sectors` first")
        t = allocation.run(cfg, use, economy)["allocation"]
        cols = ["geo", "label", "case", "gwh_per_year", "value_added_meur", "share_of_gdp"]
        print(t[t["case"] == "central"][cols].round(4).to_string(index=False))
    if wanted("figures"):
        tables = {name: df for name in TABLES if (df := _read(cfg, name)) is not None}
        for path in figures.run(cfg, tables):
            print(path)


if __name__ == "__main__":
    main()
