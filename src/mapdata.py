"""Writes docs/map_data.js for the interactive map: Small Area shapes with their numbers, and
the existing and proposed stations with their results."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from config import DOCS, MAX_KM
import model as M


def _square(lon, lat, km=0.12):
    """Stand-in shape for areas without a polygon (demo data)."""
    dy = km / 2 / M.KM_LAT
    dx = km / 2 / (111.32 * np.cos(np.radians(lat)))
    return [[[lon - dx, lat - dy], [lon + dx, lat - dy], [lon + dx, lat + dy], [lon - dx, lat + dy], [lon - dx, lat - dy]]]


def _simplify(rings, nd=4):
    out = []
    for r in rings:
        pts, last = [], None
        for x, y in r:
            p = (round(x, nd), round(y, nd))
            if p != last:
                pts.append(p)
                last = p
        if len(pts) >= 4:
            out.append(pts)
    return out


def write(sa: pd.DataFrame, shapes: dict, existing: pd.DataFrame, new_pts: pd.DataFrame,
          results: pd.DataFrame, p_cork, p_dart, growth_hi: float) -> None:
    de, ie = M.nearest(sa, existing)
    dn, inn = M.nearest(sa, new_pts)
    keep = (de < MAX_KM) | (dn < MAX_KM)
    trav = sa["travellers"].to_numpy()

    def gains(p):
        if p is None:
            return np.zeros(len(sa))
        g = trav * np.clip(M.p_at(p, dn) - M.p_at(p, de), 0, None)
        return np.where(dn < de, g, 0.0)

    g_cork, g_dart = gains(p_cork), gains(p_dart)
    feats = []
    for k in np.flatnonzero(keep):
        r = sa.iloc[k]
        rings = shapes.get(str(r["sa"])) or _square(r["lon"], r["lat"])
        t = float(r["travellers"])
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": _simplify(rings)},
            "properties": {
                "sa": str(r["sa"]), "ed": str(r["ed"]), "pop": int(r["pop"]), "trav": int(t),
                "car": int(r["car"]), "rail": int(r["rail"]), "bus": int(r["bus"]), "wc": int(r["walk_cycle"]),
                "carPct": round(100 * r["car"] / t, 1) if t else None,
                "railPct": round(100 * r["rail"] / t, 2) if t else None,
                "dEx": round(float(de[k]), 2), "nEx": str(existing["name"].iloc[ie[k]]),
                "dNew": round(float(dn[k]), 2), "nNew": str(new_pts["station"].iloc[inn[k]]),
                "gCork": round(float(g_cork[k]), 2), "gDart": round(float(g_dart[k] * growth_hi), 2),
            },
        })
    stations_new = []
    for _, r in results.iterrows():
        stations_new.append({k: (None if isinstance(v, float) and np.isnan(v) else v)
                             for k, v in r.items() if k in {
                                 "station", "line", "confidence", "pop_1km", "pop_2km", "car_commuters_1km",
                                 "car_commuters_2km", "pop_new_to_rail_1km", "cork_2022", "cork_2022_low",
                                 "cork_2022_high", "dart_2022", "dart_2040_low", "dart_2040_high",
                                 "top3_by_car_1km_pct"}}
                            | {"lat": float(new_pts.set_index("station").loc[r["station"], "lat"]),
                               "lon": float(new_pts.set_index("station").loc[r["station"], "lon"]),
                               "note": str(new_pts.set_index("station").loc[r["station"], "note"])})
    data = {"areas": {"type": "FeatureCollection", "features": feats},
            "existing": [{"name": n, "lat": float(a), "lon": float(b)}
                         for n, a, b in existing[["name", "lat", "lon"]].itertuples(index=False)],
            "proposed": stations_new}
    (DOCS / "map_data.js").write_text("window.MAP_DATA = " + json.dumps(data, separators=(",", ":"), default=float) + ";\n")
