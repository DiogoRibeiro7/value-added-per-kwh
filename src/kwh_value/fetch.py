"""Downloads, each cached under ``data/raw`` so that a second run makes no request.

* Our World in Data's energy dataset, pinned to one commit of its GitHub repository and checked
  against a SHA-256 digest, so the cross-country figures can be reproduced exactly.
* Eurostat tables through the SDMX 2.1 dissemination API, as uncompressed TSV: final electricity
  consumption by sector (``nrg_bal_c``), gross value added by industry (``nama_10_a64``) and GDP
  (``nama_10_gdp``). Eurostat revises its tables; the file of each query is kept as downloaded.
"""

from __future__ import annotations

import hashlib
import io
import logging
import time
from collections.abc import Callable

import pandas as pd

log = logging.getLogger(__name__)


def _get(
    url: str, timeout_s: float = 120, retries: int = 3, sleep: Callable[[float], None] = time.sleep
) -> bytes:
    import requests

    from . import __version__

    headers = {"User-Agent": f"kwh-value/{__version__} (python-requests)"}
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=timeout_s, headers=headers)
        except OSError:  # connection errors and timeouts
            if attempt == retries:
                raise
        else:
            if resp.status_code < 500 and resp.status_code != 429 or attempt == retries:
                resp.raise_for_status()
                return resp.content
        log.warning("attempt %d for %s failed; retrying", attempt, url)
        sleep(30 * attempt)
    raise RuntimeError("unreachable")  # pragma: no cover


def owid(cfg, get: Callable[[str], bytes] | None = None, force: bool = False) -> pd.DataFrame:
    """The OWID energy dataset at the pinned commit."""
    src = cfg.raw["countries"]["owid"]
    path = cfg.path("raw") / "owid-energy-data.csv"
    if force or not path.exists():
        data = (get or _get)(src["url"])
        digest = hashlib.sha256(data).hexdigest()
        if src.get("sha256") and digest != src["sha256"]:
            raise ValueError(f"OWID file digest {digest} does not match the pinned one")
        path.write_bytes(data)
    return pd.read_csv(path)


def read_tsv(text: str) -> pd.DataFrame:
    """Parse a Eurostat SDMX 2.1 TSV response into long form.

    The first column holds the comma-separated dimension codes and its header ends in
    ``\\TIME_PERIOD``; each further column is a period. A value can carry flags after a space
    (``1598588.0 p``); ``:`` means not available.
    """
    raw = pd.read_csv(io.StringIO(text), sep="\t", dtype=str)
    first = raw.columns[0]
    dims = first.split("\\")[0].split(",")
    keys = raw[first].str.split(",", expand=True)
    keys.columns = dims
    rows = []
    for period in raw.columns[1:]:
        cells = raw[period].fillna(":").str.strip()
        value = pd.to_numeric(cells.str.split(" ").str[0].replace(":", None), errors="coerce")
        flag = cells.str.split(" ", n=1).str[1].fillna("")
        rows.append(keys.assign(time=str(period).strip(), value=value, flag=flag))
    return pd.concat(rows, ignore_index=True)


def eurostat(
    cfg,
    dataset: str,
    key: str,
    start: int,
    end: int,
    get: Callable[[str], bytes] | None = None,
    force: bool = False,
) -> pd.DataFrame:
    """One SDMX query, cached by its URL."""
    base = cfg.raw["sectors"]["eurostat_api"]
    url = f"{base}/{dataset}/{key}?format=TSV&startPeriod={start}&endPeriod={end}&compressed=false"
    name = hashlib.sha1(url.encode()).hexdigest()[:12]
    path = cfg.path("raw") / "eurostat" / f"{dataset}_{name}.tsv"
    path.parent.mkdir(parents=True, exist_ok=True)
    if force or not path.exists():
        path.write_bytes((get or _get)(url))
        log.info("Eurostat: downloaded %s", url)
    return read_tsv(path.read_text(encoding="utf-8"))


def eurostat_inputs(cfg, get=None, force: bool = False) -> dict[str, pd.DataFrame]:
    """The three Eurostat tables the sector analysis needs, for the configured countries."""
    s = cfg.raw["sectors"]
    year, geos = int(s["year"]), "+".join(s["geos"])
    energy = sorted({c for m in s["mapping"].values() for c in m["energy"]} | set(s["totals"]))
    nace = sorted(
        {c for m in s["mapping"].values() for c in m["nace"] + m.get("minus", [])}
        | {"TOTAL", s["imputed_rents"]}
    )
    return {
        "electricity": eurostat(
            cfg, "nrg_bal_c", f"A.{'+'.join(energy)}.E7000.GWH.{geos}", year, year, get, force
        ),
        "value_added": eurostat(
            cfg, "nama_10_a64", f"A.CP_MEUR.{'+'.join(nace)}.B1G.{geos}", year, year, get, force
        ),
        "gdp": eurostat(cfg, "nama_10_gdp", f"A.CP_MEUR.B1GQ.{geos}", year, year, get, force),
    }
