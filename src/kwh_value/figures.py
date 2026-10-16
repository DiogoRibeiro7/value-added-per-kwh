"""Article figures. Each PNG is written next to a CSV with exactly the numbers plotted."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# Categorical slots in a validated order; every chart also carries a legend or direct labels.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
MARKERS = ["o", "s", "^", "D"]
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
OWID_NOTE = (
    "Data: Our World in Data energy dataset (electricity demand from Ember and the Energy "
    "Institute; GDP from the Maddison Project, 2011 international dollars)."
)
EUROSTAT_NOTE = (
    "Data: Eurostat, energy balances (nrg_bal_c) and national accounts by industry "
    "(nama_10_a64, nama_10_gdp), current prices."
)
GEO_NAMES = {"PT": "Portugal", "ES": "Spain"}


def style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "font.family": "sans-serif",
            "font.size": 10,
            "axes.edgecolor": AXIS,
            "axes.labelcolor": INK_2,
            "axes.titlecolor": INK,
            "axes.titlesize": 11,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelcolor": INK_2,
            "ytick.labelcolor": INK_2,
            "legend.frameon": False,
            "legend.labelcolor": INK_2,
            "lines.linewidth": 1.6,
            "lines.markersize": 5,
        }
    )


def _title(fig, title: str) -> None:
    fig.text(0.01, 0.99, title, ha="left", va="top", color=INK, fontsize=12)


def _legend(fig, handles, labels, ncol: int, y: float = 0.93) -> None:
    fig.legend(
        handles,
        labels,
        loc="upper left",
        bbox_to_anchor=(0.01, y),
        ncol=ncol,
        fontsize=9,
        handlelength=1.8,
    )


def _finish(fig, path: Path, data: pd.DataFrame, note: str) -> Path:
    fig.text(0.01, 0.005, note, color=MUTED, fontsize=7.5, ha="left", va="bottom")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    data.to_csv(path.with_suffix(".csv"), index=False)
    return path


def _euro_axis(axis) -> None:
    axis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, _: f"€{v:g}" if v >= 1 else f"€{v:.2g}")
    )


def countries(
    panel: pd.DataFrame,
    fit: pd.DataFrame,
    smelters: pd.DataFrame,
    labels: list[str],
    out: Path,
    floor_kwh: float = 1000,
    smelter_share: float = 0.1,
    offsets: dict | None = None,
) -> Path:
    """Electricity demand per person against GDP per person, log scales."""
    fig, ax = plt.subplots(figsize=(9.4, 6.4))
    big = smelters[smelters["smelting_share"] >= smelter_share] if len(smelters) else smelters
    hosts = set(big["country"]) if len(big) else set()
    is_host = panel["country"].isin(hosts)
    ax.scatter(
        panel.loc[~is_host, "gdp_per_capita"],
        panel.loc[~is_host, "kwh_per_capita"],
        s=18,
        color=SERIES[0],
        alpha=0.55,
        linewidth=0,
        label="Country, 2022",
    )
    ax.scatter(
        panel.loc[is_host, "gdp_per_capita"],
        panel.loc[is_host, "kwh_per_capita"],
        s=34,
        color=SERIES[1],
        marker="s",
        linewidth=0,
        label=f"Aluminium smelting takes {smelter_share:.0%} or more of national electricity",
    )
    f = fit.iloc[0]
    x = np.geomspace(panel["gdp_per_capita"].min(), panel["gdp_per_capita"].max(), 50)
    ax.plot(
        x,
        np.exp(f["intercept"]) * x ** f["slope"],
        color=INK_2,
        linewidth=1.2,
        label=f"Log-log fit, slope {f['slope']:.2f}, R² {f['r2']:.2f}",
    )
    ax.axhline(
        floor_kwh,
        color=MUTED,
        linestyle="--",
        linewidth=1.0,
        label=f"{floor_kwh:,.0f} kWh per person",
    )
    offsets = offsets or {}
    for _, r in panel[panel["country"].isin(labels)].iterrows():
        dx, dy = offsets.get(r["country"], (4, 3))
        ax.annotate(
            r["country"],
            (r["gdp_per_capita"], r["kwh_per_capita"]),
            fontsize=8,
            color=INK,
            xytext=(dx, dy),
            textcoords="offset points",
            ha="right" if dx < 0 else "left",
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_xlabel("GDP per person (2011 international dollars, PPP)")
    ax.set_ylabel("Electricity demand per person (kWh)")
    _title(fig, "Electricity use and income across countries, 2022")
    handles, labels_ = ax.get_legend_handles_labels()
    _legend(fig, handles, labels_, 2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.86))
    cols = [
        "country",
        "iso_code",
        "gdp_per_capita",
        "kwh_per_capita",
        "gdp_per_kwh",
        "ratio_to_line",
    ]
    return _finish(fig, out / "countries.png", panel[cols], OWID_NOTE)


def sectors(sector: pd.DataFrame, economy: pd.DataFrame, out: Path) -> Path:
    """Gross value added per kWh by sector and country, log scale."""
    geos = list(dict.fromkeys(sector["geo"]))
    order = sector.groupby("sector")["eur_per_kwh"].mean().sort_values().index.tolist()
    y = {s: i for i, s in enumerate(order)}
    fig, ax = plt.subplots(figsize=(9.4, 0.42 * len(order) + 2.2))
    for k, geo in enumerate(geos):
        d = sector[sector["geo"] == geo]
        offset = (k - (len(geos) - 1) / 2) * 0.18
        ax.scatter(
            d["eur_per_kwh"],
            d["sector"].map(y) + offset,
            color=SERIES[k],
            marker=MARKERS[k],
            s=36,
            zorder=3,
            label=GEO_NAMES.get(geo, geo),
        )
        e = economy[economy["geo"] == geo].iloc[0]
        ax.axvline(
            e["gdp_per_kwh_final"],
            color=SERIES[k],
            linestyle="--",
            linewidth=1.0,
            label=f"{GEO_NAMES.get(geo, geo)}: GDP per kWh of final electricity "
            f"(€{e['gdp_per_kwh_final']:.2f})",
        )
    ax.set_yticks(range(len(order)), order)
    ax.set_xscale("log")
    _euro_axis(ax.xaxis)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Gross value added per kWh of electricity used (euros, log scale)")
    year = int(economy["year"].iloc[0])
    _title(fig, f"Value added per kWh of electricity by sector, {year}")
    handles, labels = ax.get_legend_handles_labels()
    _legend(fig, handles, labels, 2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.84))
    cols = ["geo", "sector", "gwh", "va_meur", "eur_per_kwh", "share_of_covered_electricity"]
    return _finish(fig, out / "sectors.png", sector[cols], EUROSTAT_NOTE)


def uses(
    use: pd.DataFrame, sector: pd.DataFrame, economy: pd.DataFrame, geo: str, out: Path, note: str
) -> Path:
    """Revenue and value added per kWh for specific uses, against sector benchmarks."""
    labels = list(dict.fromkeys(use["label"]))
    floor = 0.01  # left edge of the axis, EUR per kWh
    fig, ax = plt.subplots(figsize=(9.4, 0.62 * len(labels) + 2.4))
    rows = []
    for i, label in enumerate(labels):
        d = use[use["label"] == label].set_index("case")
        for j, (col, name) in enumerate(
            (
                ("revenue_eur_per_kwh", "Revenue per kWh"),
                ("value_added_eur_per_kwh", "Value added per kWh"),
            )
        ):
            y = i + (0.14 if j == 0 else -0.14)
            lo, mid, hi = (d.loc[c, col] for c in ("low", "central", "high"))
            # A log axis cannot show zero or a loss: such values sit at the left edge, marked.
            shown = [max(v, floor) for v in (lo, mid, hi)]
            ax.plot([shown[0], shown[2]], [y, y], color=SERIES[j], linewidth=2.2, alpha=0.6)
            ax.scatter(
                [shown[1]],
                [y],
                color=SERIES[j],
                marker=MARKERS[j] if mid >= floor else "<",
                s=40,
                zorder=3,
                label=name if i == 0 else None,
            )
            if lo < floor:
                text = f"central €{mid:.3f}" if mid < floor else ""
                text += ("; " if text else "") + ("low case below zero" if lo < 0 else "")
                ax.annotate(
                    text.strip("; "),
                    (floor, y),
                    xytext=(10, -11),
                    textcoords="offset points",
                    fontsize=8,
                    color=INK_2,
                )
            rows.append({"use": label, "measure": name, "low": lo, "central": mid, "high": hi})
    s = sector[sector["geo"] == geo].set_index("sector")["eur_per_kwh"]
    e = economy[economy["geo"] == geo].iloc[0]
    refs = [
        ("GDP per kWh", e["gdp_per_kwh_final"], INK),
        ("services, value added per kWh", s.get("Services", np.nan), SERIES[2]),
        ("basic metals, value added per kWh", s.get("Basic metals", np.nan), SERIES[3]),
    ]
    for name, value, color in refs:
        ax.axvline(
            value,
            color=color,
            linestyle="--",
            linewidth=1.0,
            label=f"{GEO_NAMES.get(geo, geo)}, {name}: €{value:.2f}",
        )
        rows.append(
            {
                "use": f"reference: {name}",
                "measure": "value added per kWh",
                "low": value,
                "central": value,
                "high": value,
            }
        )
    ax.set_yticks(range(len(labels)), labels)
    ax.set_ylim(-0.6, len(labels) - 0.4)
    ax.set_xscale("log")
    ax.set_xlim(left=floor * 0.8)
    _euro_axis(ax.xaxis)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Euros per kWh (log scale); bars: low to high case, marker: central case")
    _title(fig, "Revenue and value added per kWh: specific uses against sector averages")
    handles, labels_ = ax.get_legend_handles_labels()
    _legend(fig, handles, labels_, 2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.8))
    return _finish(fig, out / "uses.png", pd.DataFrame(rows), note)


def run(cfg, tables: dict[str, pd.DataFrame]) -> list[Path]:
    style()
    out = cfg.figures
    made = []
    if "country_panel" in tables:
        made.append(
            countries(
                tables["country_panel"],
                tables["country_fit"],
                tables["country_smelters"],
                cfg.raw["figures"]["country_labels"],
                out,
                smelter_share=float(cfg.raw["figures"].get("smelter_share", 0.1)),
                offsets=cfg.raw["figures"].get("country_label_offsets"),
            )
        )
    if "sector_value_added" in tables:
        made.append(sectors(tables["sector_value_added"], tables["economy_value_added"], out))
        if "use_value_added" in tables:
            made.append(
                uses(
                    tables["use_value_added"],
                    tables["sector_value_added"],
                    tables["economy_value_added"],
                    cfg.raw["figures"]["uses_geo"],
                    out,
                    cfg.raw["figures"]["uses_note"],
                )
            )
    return made
