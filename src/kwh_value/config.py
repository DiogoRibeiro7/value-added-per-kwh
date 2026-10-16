"""Configuration loading. The YAML file holds every source, mapping and assumption."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = Path("config/default.yaml")


@dataclass(frozen=True)
class Config:
    raw: dict[str, Any]
    root: Path
    file: Path | None = None

    def path(self, key: str) -> Path:
        p = self.root / self.raw["paths"][key]
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def tables(self) -> Path:
        return self.path("tables")

    @property
    def figures(self) -> Path:
        return self.path("figures")

    @property
    def geos(self) -> list[str]:
        return list(self.raw["sectors"]["geos"])


def load_config(path: str | Path = DEFAULT_CONFIG) -> Config:
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    # Paths in the YAML are relative to the repository root (the config file's parent's parent).
    return Config(raw=raw, root=path.resolve().parent.parent, file=path.resolve())
