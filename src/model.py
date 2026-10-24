"""Catchments, distance-decay curves and the new-station estimate.

The share of people who take the train to work falls with distance from the nearest station.
That curve is measured twice: around Cork's existing commuter stations (today's service), and
around north-east Dublin DART stations (a frequent service, used as an upper analogue). A new
station moves some homes closer to rail; the extra rail commuters are the people in those homes
times the rise in the curve between their old and new distance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import BANDS, CATCH_KM, GROWTH_2016_2040, MAX_KM, POP_CORK_2016, POP_CORK_2022

KM_LAT = 110.574


def dist_km(lat1, lon1, lat2, lon2):
    """Equirectangular distance in km; accurate to well under 1% over a city region."""
    lat1, lon1, lat2, lon2 = map(np.asarray, (lat1, lon1, lat2, lon2))
    k_lon = 111.320 * np.cos(np.radians((lat1 + lat2) / 2))
    return np.hypot((lon2 - lon1) * k_lon, (lat2 - lat1) * KM_LAT)


def nearest(sa: pd.DataFrame, st: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Distance to, and index of, the nearest station for every Small Area."""
    d = dist_km(sa["lat"].to_numpy()[:, None], sa["lon"].to_numpy()[:, None],
                st["lat"].to_numpy()[None, :], st["lon"].to_numpy()[None, :])
    i = d.argmin(axis=1)
    return d[np.arange(len(sa)), i], i


def band_of(d: np.ndarray) -> np.ndarray:
    """Band index for each distance; -1 beyond the last band."""
    b = np.searchsorted(BANDS, d, side="right") - 1
    return np.where(d >= BANDS[-1], -1, b)


def curve(trav: np.ndarray, rail: np.ndarray, d: np.ndarray) -> np.ndarray:
    """Rail share of people who travel to work, per distance band."""
    b = band_of(d)
    n = len(BANDS) - 1
    t = np.bincount(b[b >= 0], weights=trav[b >= 0], minlength=n)
    r = np.bincount(b[b >= 0], weights=rail[b >= 0], minlength=n)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = np.where(t > 0, r / t, np.nan)
    # an empty band takes its neighbour's value so predictions never fail silently
    p = pd.Series(p).ffill().bfill().to_numpy()
    return p


def curve_table(trav, rail, d, label: str) -> pd.DataFrame:
    b = band_of(d)
    rows = []
    for k in range(len(BANDS) - 1):
        m = b == k
        rows.append({"curve": label, "band": f"{BANDS[k]:g}–{BANDS[k + 1]:g} km", "band_mid_km": (BANDS[k] + BANDS[k + 1]) / 2,
                     "small_areas": int(m.sum()), "travellers": float(trav[m].sum()),
                     "rail": float(rail[m].sum()),
                     "rail_share_pct": 100 * rail[m].sum() / trav[m].sum() if trav[m].sum() else np.nan})
    return pd.DataFrame(rows)


def p_at(p: np.ndarray, d: np.ndarray) -> np.ndarray:
    b = band_of(np.asarray(d))
    return np.where(b >= 0, p[np.clip(b, 0, None)], 0.0)


def leave_one_out(sa: pd.DataFrame, st: pd.DataFrame) -> pd.DataFrame:
    """For each existing station, fit the curve without its catchment and predict its rail
    commuters. Tests whether distance alone explains station use."""
    d, i = nearest(sa, st)
    keep = d < MAX_KM
    out = []
    for k, name in enumerate(st["name"]):
        mine = keep & (i == k)
        if mine.sum() < 3:
            continue
        others = keep & ~mine
        p = curve(sa["travellers"].to_numpy()[others], sa["rail"].to_numpy()[others], d[others])
        pred = float((sa["travellers"].to_numpy()[mine] * p_at(p, d[mine])).sum())
        out.append({"station": name, "small_areas": int(mine.sum()),
                    "travellers": float(sa["travellers"][mine].sum()),
                    "actual_rail": float(sa["rail"][mine].sum()), "predicted_rail": pred})
    return pd.DataFrame(out)


def reach(sa: pd.DataFrame, new: pd.DataFrame, existing: pd.DataFrame) -> pd.DataFrame:
    """People living within 1 and 2 km of each new station (each area counted once, for its
    nearest new station), and how many of them are not already within that distance of rail."""
    dn, ino = nearest(sa, new)
    de, _ = nearest(sa, existing)
    rows = []
    for k, name in enumerate(new["station"]):
        r = {"station": name}
        for km in CATCH_KM:
            m = (ino == k) & (dn <= km)
            fresh = m & (de > km)
            r[f"pop_{km:g}km"] = float(sa["pop"][m].sum())
            r[f"car_commuters_{km:g}km"] = float(sa["car"][m].sum())
            r[f"travellers_{km:g}km"] = float(sa["travellers"][m].sum())
            r[f"pop_new_to_rail_{km:g}km"] = float(sa["pop"][fresh].sum())
        rows.append(r)
    return pd.DataFrame(rows)


def extra_commuters(sa: pd.DataFrame, new: pd.DataFrame, existing: pd.DataFrame, p: np.ndarray) -> pd.Series:
    """Extra daily rail commuters each new station would add, under curve p."""
    dn, ino = nearest(sa, new)
    de, _ = nearest(sa, existing)
    gain = sa["travellers"].to_numpy() * np.clip(p_at(p, dn) - p_at(p, de), 0, None)
    gain = np.where(dn < de, gain, 0.0)
    s = pd.Series(np.bincount(ino, weights=gain, minlength=len(new)), index=new["station"].to_numpy())
    return s


def bootstrap_extras(sa, new, existing, calib_trav, calib_rail, calib_d, n, rng) -> pd.DataFrame:
    """Uncertainty from the curve: resample the calibration areas, refit, re-predict."""
    m = len(calib_trav)
    draws = []
    for _ in range(n):
        j = rng.integers(0, m, m)
        p = curve(calib_trav[j], calib_rail[j], calib_d[j])
        draws.append(extra_commuters(sa, new, existing, p).to_numpy())
    a = np.array(draws)
    return pd.DataFrame({"station": new["station"].to_numpy(), "low": np.percentile(a, 2.5, axis=0),
                         "high": np.percentile(a, 97.5, axis=0)})


def shift_stations(new: pd.DataFrame, metres: float, rng) -> pd.DataFrame:
    s = new.copy()
    r = metres / 1000 * np.sqrt(rng.uniform(0, 1, len(s)))
    th = rng.uniform(0, 2 * np.pi, len(s))
    s["lat"] = s["lat"] + r * np.sin(th) / KM_LAT
    s["lon"] = s["lon"] + r * np.cos(th) / (111.320 * np.cos(np.radians(s["lat"])))
    return s


def location_sensitivity(sa, new, existing, p, n, metres, rng) -> pd.DataFrame:
    """Stations' positions are approximate: move each by up to `metres` and recompute."""
    ex, car, rank1 = [], [], []
    for _ in range(n):
        s = shift_stations(new, metres, rng)
        e = extra_commuters(sa, s, existing, p).to_numpy()
        c = reach(sa, s, existing)["car_commuters_1km"].to_numpy()
        ex.append(e)
        car.append(c)
        rank1.append(np.argsort(-c).argsort())  # 0 = most car commuters within 1 km
    ex, car, rank1 = map(np.array, (ex, car, rank1))
    return pd.DataFrame({
        "station": new["station"].to_numpy(),
        "extra_min": ex.min(axis=0), "extra_max": ex.max(axis=0),
        "car_1km_min": car.min(axis=0), "car_1km_max": car.max(axis=0),
        "top3_by_car_1km_pct": 100 * (rank1 < 3).mean(axis=0),
    })


def growth_2040() -> tuple[float, float]:
    """Growth from 2022 to 2040 implied by CMATS (50-60% from 2016) after netting off 2016-22."""
    f = POP_CORK_2016 / POP_CORK_2022
    return GROWTH_2016_2040[0] * f, GROWTH_2016_2040[1] * f
