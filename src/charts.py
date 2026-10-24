"""Figures. Blue = Cork today; orange = DART analogue (frequent service); grey = context."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

BLUE, ORANGE, GREY, INK, MUTED, GRID = "#1f5f8b", "#c4661f", "#a3abb3", "#1d2733", "#5b6672", "#e3e6e9"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "axes.axisbelow": True, "figure.dpi": 150,
    "savefig.bbox": "tight",
})


def curves(tab: pd.DataFrame, path):
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    for label, col in [("Cork today", BLUE), ("Dublin DART suburbs", ORANGE)]:
        t = tab[tab["curve"] == label]
        ax.plot(t["band_mid_km"], t["rail_share_pct"], "-o", color=col, lw=2, ms=6, label=label)
    ax.set_xlabel("Distance from home to nearest station (km, band middle)")
    ax.set_ylabel("% of commuters going by train")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False)
    fig.savefig(path)
    plt.close(fig)


def validation(lo: pd.DataFrame, path):
    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    m = max(lo["actual_rail"].max(), lo["predicted_rail"].max()) * 1.1
    ax.plot([0, m], [0, m], color=GREY, lw=1)
    ax.scatter(lo["actual_rail"], lo["predicted_rail"], s=48, color=BLUE, edgecolor="white", linewidth=1.5, zorder=3)
    for _, r in lo.iterrows():
        ax.annotate(r["station"], (r["actual_rail"], r["predicted_rail"]), xytext=(5, 3),
                    textcoords="offset points", fontsize=8, color=INK)
    ax.set_xlim(0, m)
    ax.set_ylim(0, m)
    ax.set_xlabel("Actual rail commuters, Census 2022")
    ax.set_ylabel("Predicted (station left out of the fit)")
    fig.savefig(path)
    plt.close(fig)


def reach_bars(r: pd.DataFrame, path):
    r = r.sort_values("car_commuters_2km")
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    y = np.arange(len(r))
    ax.barh(y, r["car_commuters_2km"], color=GREY, label="within 2 km")
    ax.barh(y, r["car_commuters_1km"], color=BLUE, label="within 1 km")
    ax.set_yticks(y, r["station"])
    ax.set_xlabel("People who drive or are driven to work (Census 2022)")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(axis="y", visible=False)
    fig.savefig(path)
    plt.close(fig)


def extras(e: pd.DataFrame, path):
    e = e.sort_values("dart_2040_high")
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    y = np.arange(len(e))
    ax.hlines(y, e["cork_2022"], e["dart_2040_high"], color=GRID, lw=6, zorder=1)
    ax.scatter(e["cork_2022"], y, color=BLUE, s=40, zorder=3, label="Today's Cork service, 2022 population")
    ax.scatter(e["dart_2040_high"], y, color=ORANGE, s=40, zorder=3, label="DART-like service, 2040 population (high)")
    ax.set_yticks(y, e["station"])
    ax.set_xlabel("Extra people taking the train to work each day")
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    ax.grid(axis="y", visible=False)
    fig.savefig(path)
    plt.close(fig)


def map_(sa: pd.DataFrame, existing: pd.DataFrame, new: pd.DataFrame, path):
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    s = sa[sa["travellers"] > 0]
    share = s["car"] / s["travellers"]
    sc = ax.scatter(s["lon"], s["lat"], s=np.clip(s["travellers"] / 12, 2, 30), c=100 * share, cmap="Greys",
                    vmin=20, vmax=90, alpha=0.75, linewidths=0)
    ax.scatter(existing["lon"], existing["lat"], marker="s", s=46, color=BLUE, edgecolor="white", label="Existing station", zorder=3)
    ax.scatter(new["lon"], new["lat"], marker="o", s=60, color=ORANGE, edgecolor="white", label="Proposed station (approx.)", zorder=4)
    for k, (_, r) in enumerate(new.iterrows()):
        dy = 6 if k % 2 == 0 else -12     # alternate above and below so neighbours do not collide
        ax.annotate(r["station"], (r["lon"], r["lat"]), xytext=(4, dy), textcoords="offset points", fontsize=7.5, color=INK)
    lat0 = np.radians(s["lat"].mean())
    ax.set_aspect(1 / np.cos(lat0))
    ax.set_xlim(-8.62, -8.15)
    ax.set_ylim(51.83, 51.97)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.colorbar(sc, ax=ax, shrink=0.7, label="% of commuters going by car")
    ax.legend(frameon=False, loc="lower left", fontsize=8)
    fig.savefig(path)
    plt.close(fig)
