"""Synthetic Small Areas with a known distance-decay, for tests and an offline dry run."""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import CORK_FALLBACK, DART_ANALOGUE


def true_share(d, top, scale):
    return top * np.exp(-np.asarray(d) / scale)


def make(seed=3, n_cork=2500, n_dub=900):
    rng = np.random.default_rng(seed)
    cork_st = pd.DataFrame([{"name": k, "code": "", "lat": v[0], "lon": v[1]} for k, v in CORK_FALLBACK.items()])
    dub_st = pd.DataFrame({"name": DART_ANALOGUE, "code": "",
                           "lat": np.linspace(53.36, 53.45, len(DART_ANALOGUE)),
                           "lon": np.linspace(-6.21, -6.08, len(DART_ANALOGUE))})

    def areas(st, n, top, scale, tag):
        k = rng.integers(0, len(st), n)
        r = rng.exponential(1.6, n)
        th = rng.uniform(0, 2 * np.pi, n)
        lat = st["lat"].to_numpy()[k] + r * np.sin(th) / 110.574
        lon = st["lon"].to_numpy()[k] + r * np.cos(th) / (111.32 * np.cos(np.radians(lat)))
        trav = rng.integers(60, 200, n).astype(float)
        from model import nearest  # noqa: PLC0415
        df = pd.DataFrame({"lat": lat, "lon": lon})
        d, _ = nearest(df, st)
        rail = rng.binomial(trav.astype(int), true_share(d, top, scale)).astype(float)
        car = np.round(trav * 0.6)
        return pd.DataFrame({"sa": [f"{tag}{i}" for i in range(n)], "ed": "demo", "la": tag, "lon": lon,
                             "lat": lat, "pop": trav * 2.1, "rail": rail, "car": car, "bus": 0.0,
                             "walk_cycle": 0.0, "travellers": trav})

    return (areas(cork_st, n_cork, 0.06, 1.5, "C"), areas(dub_st, n_dub, 0.22, 1.2, "D"),
            cork_st, dub_st)
