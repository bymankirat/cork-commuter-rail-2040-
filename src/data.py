"""Downloads: Census 2022 Small Areas (with travel to work) and Irish Rail station positions.

Small Areas come from the CSO Census Hub feature service, page by page, inside a lon/lat box,
with polygons in lon/lat. Each Small Area is represented by its polygon centroid.
"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

from config import (CORK_FALLBACK, PAGE, RAW, SA_FIELDS, SA_LAYER, STATIONS_URL)


def _get(url: str, timeout: int = 120) -> bytes:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:  # noqa: BLE001  some Python installs lack certificates; curl usually works
        return subprocess.run(["curl", "-sSL", "--max-time", str(timeout), url],
                              capture_output=True, check=True).stdout


def _get_retry(url: str, tries: int = 5) -> bytes:
    last = None
    for k in range(tries):
        try:
            return _get(url)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"could not download {url[:120]}: {last}")


def ring_centroid(rings: list) -> tuple[float, float]:
    """Area-weighted centroid of polygon rings (lon, lat). Holes have the opposite winding,
    so their signed area subtracts automatically."""
    a_sum = cx = cy = 0.0
    for ring in rings:
        p = np.asarray(ring, dtype=float)
        if len(p) < 3:
            continue
        x, y = p[:, 0], p[:, 1]
        x1, y1 = np.roll(x, -1), np.roll(y, -1)
        cross = x * y1 - x1 * y
        a = cross.sum() / 2
        if a == 0:
            continue
        a_sum += a
        cx += ((x + x1) * cross).sum() / 6
        cy += ((y + y1) * cross).sum() / 6
    if a_sum == 0:
        p = np.asarray(rings[0], dtype=float)
        return float(p[:, 0].mean()), float(p[:, 1].mean())
    return cx / a_sum, cy / a_sum


def _query_url(box, offset: int) -> str:
    params = {
        "where": "1=1", "geometry": ",".join(str(v) for v in box),
        "geometryType": "esriGeometryEnvelope", "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
        "outFields": ",".join(SA_FIELDS), "returnGeometry": "true", "outSR": "4326",
        "maxAllowableOffset": "0.0002", "geometryPrecision": "5", "orderByFields": "ObjectId",
        "resultOffset": str(offset), "resultRecordCount": str(PAGE), "f": "json",
    }
    return SA_LAYER + "?" + urllib.parse.urlencode(params)


def download_small_areas(box, name: str) -> Path:
    out = RAW / f"small_areas_{name}.csv"
    geo = RAW / f"small_areas_{name}_shapes.json"
    if out.exists() and out.stat().st_size > 1000 and geo.exists():
        return out
    RAW.mkdir(parents=True, exist_ok=True)
    rows, shapes, offset = [], {}, 0
    while True:
        payload = json.loads(_get_retry(_query_url(box, offset)))
        if "error" in payload:
            raise RuntimeError(f"Census Hub error: {payload['error']}")
        feats = payload.get("features", [])
        for f in feats:
            a = f["attributes"]
            g = f.get("geometry") or {}
            if not g.get("rings"):
                continue
            lon, lat = ring_centroid(g["rings"])
            shapes[str(a.get("GEOGID"))] = [[[round(x, 5), round(y, 5)] for x, y in r] for r in g["rings"]]
            rows.append({**{k: a.get(k) for k in SA_FIELDS}, "lon": lon, "lat": lat})
        print(f"  {name}: {len(rows):,} small areas", flush=True)
        if not feats or not payload.get("exceededTransferLimit") and len(feats) < PAGE:
            break
        offset += len(feats)
    pd.DataFrame(rows).to_csv(out, index=False)
    geo.write_text(json.dumps(shapes))
    return out


def load_shapes(name: str) -> dict:
    f = RAW / f"small_areas_{name}_shapes.json"
    return json.loads(f.read_text()) if f.exists() else {}


def download_stations() -> Path:
    out = RAW / "stations.csv"
    if out.exists() and out.stat().st_size > 1000:
        return out
    RAW.mkdir(parents=True, exist_ok=True)
    root = ET.fromstring(_get_retry(STATIONS_URL))
    rows = []
    for st in root.iter():
        if not st.tag.endswith("objStation"):
            continue
        rec = {child.tag.split("}")[-1]: (child.text or "").strip() for child in st}
        rows.append({"name": rec.get("StationDesc"), "code": rec.get("StationCode"),
                     "lat": float(rec.get("StationLatitude") or "nan"),
                     "lon": float(rec.get("StationLongitude") or "nan")})
    df = pd.DataFrame(rows).dropna()
    if len(df) < 50:
        raise RuntimeError(f"station list looks wrong ({len(df)} stations)")
    df.to_csv(out, index=False)
    return out


def load_stations() -> tuple[pd.DataFrame, str]:
    """All stations from the API; falls back to approximate Cork positions if it is down."""
    try:
        return pd.read_csv(download_stations()), "api"
    except Exception as e:  # noqa: BLE001
        print(f"  [!] Irish Rail API unavailable ({e}); using approximate Cork positions")
        df = pd.DataFrame([{"name": k, "code": "", "lat": v[0], "lon": v[1]} for k, v in CORK_FALLBACK.items()])
        return df, "fallback"


def tidy_small_areas(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    num = [c for c in df.columns if c.startswith("T")]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce").fillna(0)
    out = pd.DataFrame({
        "sa": df["GEOGID"].astype(str), "ed": df["ED_ENGLISH"], "la": df["LOCAL_AUTHORITY"],
        "lon": df["lon"], "lat": df["lat"], "pop": df["T1_1AGETT_Norm"],
        "rail": df["T11_1_TDLW"], "car": df["T11_1_CDW"] + df["T11_1_CPW"],
        "bus": df["T11_1_BUW"], "walk_cycle": df["T11_1_FW"] + df["T11_1_BIW"],
    })
    out["travellers"] = df["T11_1_TW"] - df["T11_1_WMFHW"] - df["T11_1_NSW"]  # people who travel to work
    return out[out["travellers"] > 0].drop_duplicates("sa").reset_index(drop=True)
