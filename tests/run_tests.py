"""Offline tests: `python tests/run_tests.py`. No downloads needed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import data as D  # noqa: E402
import demo  # noqa: E402
import model as M  # noqa: E402

n_ok = 0


def check(name, cond, detail=""):
    global n_ok
    if not cond:
        raise AssertionError(f"FAILED: {name} {detail}")
    n_ok += 1
    print(f"  ok  {name} {detail}")


# 1. distances: 1 degree of latitude is about 110.6 km; Cork to Midleton about 19 km
check("1 degree latitude = 110.57 km", abs(M.dist_km(51, -8, 52, -8) - 110.574) < 1e-6)
d = float(M.dist_km(51.9018, -8.4582, 51.9192, -8.1777))
check("Kent to Midleton straight line about 19.3 km", 18.8 < d < 19.8, f"{d:.2f} km")

# 2. polygon centroid: unit square, and a square with a hole that is symmetric
sq = [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
check("square centroid (0.5, 0.5)", np.allclose(D.ring_centroid(sq), (0.5, 0.5)))
L = [[[0, 0], [0, 2], [1, 2], [1, 1], [2, 1], [2, 0], [0, 0]]]   # L-shape, area 3
cx, cy = D.ring_centroid(L)
check("L-shape centroid (5/6, 5/6)", np.allclose((cx, cy), (5 / 6, 5 / 6)), f"({cx:.4f}, {cy:.4f})")

# 3. bands
check("band edges", list(M.band_of(np.array([0, 0.49, 0.5, 2.9, 4.99, 5.0, 9]))) == [0, 0, 1, 4, 5, -1, -1])

# 4. the curve recovers a planted distance-decay
cork, dub, cst, dst = demo.make()
dc, _ = M.nearest(cork, cst)
p = M.curve(cork["travellers"].to_numpy(), cork["rail"].to_numpy(), dc)
mid = np.array([(M.BANDS[k] + M.BANDS[k + 1]) / 2 for k in range(len(M.BANDS) - 1)])
truth = demo.true_share(mid, 0.06, 1.5)
check("Cork curve within 0.012 of planted shares", np.nanmax(np.abs(p - truth)) < 0.012,
      f"max error {np.nanmax(np.abs(p - truth)):.4f}")
check("curve falls with distance", p[0] > p[2] > p[-1])

# 5. leave-one-out predictions close to actual on synthetic data
lo = M.leave_one_out(cork, cst)
ratio = lo["predicted_rail"].sum() / lo["actual_rail"].sum()
check("leave-one-out total within 10%", abs(ratio - 1) < 0.10, f"ratio {ratio:.3f}")

# 6. a new station on top of an existing one adds nothing; one in empty space adds nothing
same = pd.DataFrame({"station": ["dup"], "lat": [cst["lat"][0]], "lon": [cst["lon"][0]]})
check("new station at an existing station adds ~0", M.extra_commuters(cork, same, cst, p).sum() < 1e-9)
far = pd.DataFrame({"station": ["sea"], "lat": [51.0], "lon": [-9.5]})
check("new station far from homes adds 0", M.extra_commuters(cork, far, cst, p).sum() == 0)

# 7. hand-checked arithmetic: one area 1.2 km from new, 3.5 km from old
sa = pd.DataFrame({"lat": [0.0], "lon": [0.0], "travellers": [100.0], "pop": [250.0], "car": [60.0], "rail": [0.0]})
new = pd.DataFrame({"station": ["N"], "lat": [1.2 / 110.574], "lon": [0.0]})
old = pd.DataFrame({"name": ["O"], "lat": [-3.5 / 110.574], "lon": [0.0]})
pp = np.array([0.10, 0.08, 0.06, 0.05, 0.04, 0.02])
e = M.extra_commuters(sa, new, old, pp).iloc[0]
check("extra = 100 x (0.06 - 0.02) = 4", abs(e - 4.0) < 1e-9, f"{e:.4f}")

# 8. reach counts each area once even when catchments overlap
two = pd.DataFrame({"station": ["A", "B"], "lat": [cst["lat"][0] + 0.004, cst["lat"][0] + 0.006],
                    "lon": [cst["lon"][0], cst["lon"][0]]})
r = M.reach(cork, two, cst)
dn, _ = M.nearest(cork, two)
check("overlapping catchments not double counted",
      abs(r["pop_1km"].sum() - cork["pop"][dn <= 1].sum()) < 1e-6)

# 9. growth factor arithmetic
g = M.growth_2040()
check("2040 growth 2022-based = 1.5 x 542868/584156 to 1.6 x ...",
      np.allclose(g, (1.5 * 542868 / 584156, 1.6 * 542868 / 584156)), f"{g[0]:.3f}-{g[1]:.3f}")

# 10. location shifts stay within the stated radius
rng = np.random.default_rng(1)
s = M.shift_stations(two, 600, rng)
moved = M.dist_km(two["lat"], two["lon"], s["lat"], s["lon"])
check("shifts within 600 m", (moved <= 0.6 + 1e-6).all(), f"max {moved.max() * 1000:.0f} m")

print(f"\nAll {n_ok} tests passed.")
