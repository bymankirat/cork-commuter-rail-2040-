"""download -> tidy -> curves -> validation -> new-station estimates -> figures -> report.

python run_pipeline.py         real data (downloads on first run, a few minutes)
python run_pipeline.py --demo  synthetic data, offline
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import charts as C  # noqa: E402
import data as D  # noqa: E402
import demo  # noqa: E402
import mapdata  # noqa: E402
import model as M  # noqa: E402
import report  # noqa: E402
from config import (BOX_CORK, BOX_DUBLIN_NE, CORK_STATIONS, DART_ANALOGUE, FIGS, MAX_KM, N_BOOT,  # noqa: E402
                    N_SHIFT, NEW_STATIONS_FILE, RESULTS, SEED, SHIFT_M)


def pick(stations: pd.DataFrame, names: list[str], label: str) -> pd.DataFrame:
    # names are compared without spaces or case: the API writes "LittleIsland" for Little Island
    norm = lambda x: "".join(str(x).lower().split())  # noqa: E731
    low = stations.assign(key=stations["name"].map(norm))
    want = [norm(n) for n in names]
    # exact name first, else a station whose name starts with it ("Howth Junction & Donaghmede")
    hit = low["key"].apply(lambda k: next((w for w in want if k == w or k.startswith(w)), None))
    out = low.assign(match=hit).dropna(subset=["match"]).drop_duplicates("match")
    missing = sorted(set(want) - set(out["match"]))  # noqa: C401
    if missing:
        print(f"  [!] {label}: not found in the station list: {missing}")
    if len(out) < len(names) // 2:
        raise SystemExit(f"Too few {label} stations found; check names in src/config.py")
    canon = {norm(n): n for n in names}
    out["name"] = out["match"].map(canon)          # show "Little Island", not the API's "LittleIsland"
    out = out.drop(columns=["key", "match"]).reset_index(drop=True)
    out["is_target"] = True
    return out


def main(argv):
    RESULTS.mkdir(exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    demo_run = "--demo" in argv
    print("1. Data")
    if demo_run:
        cork, dub, cork_st, dart_st = demo.make()
        st_source = "demo"
    else:
        stations, st_source = D.load_stations()
        cork = D.tidy_small_areas(D.download_small_areas(BOX_CORK, "cork"))
        cork_st = pick(stations, CORK_STATIONS, "Cork")
        if st_source == "api":
            dub = D.tidy_small_areas(D.download_small_areas(BOX_DUBLIN_NE, "dublin_ne"))
            dart_st = pick(stations, DART_ANALOGUE, "DART")
        else:
            dub, dart_st = None, None
    new = pd.read_csv(NEW_STATIONS_FILE)
    print(f"   Cork: {len(cork):,} small areas, {cork['travellers'].sum():,.0f} people travelling to work, "
          f"{cork['rail'].sum():,.0f} by train")

    # checks that stop the run if the data are not what the method assumes
    assert cork["travellers"].sum() > 50_000, "too few Cork commuters: download incomplete?"
    assert (cork["rail"] <= cork["travellers"]).all(), "rail commuters exceed travellers"
    assert len(cork_st) >= 8, "Cork stations missing"

    print("2. Distance-decay curves")
    dc, ic = M.nearest(cork, cork_st)
    inside = dc < M.MAX_KM
    T, R, CITY = cork["travellers"].to_numpy(), cork["rail"].to_numpy(), cork["is_city"].to_numpy(bool)
    p_cork = M.split_curves(cork, dc, inside)          # separate curves for Cork city and the county towns
    tabs = [M.curve_table(T[inside & CITY], R[inside & CITY], dc[inside & CITY], "Cork city today"),
            M.curve_table(T[inside & ~CITY], R[inside & ~CITY], dc[inside & ~CITY], "Cork towns today")]
    # city areas use less rail at any distance; the same ratio scales the DART analogue for them
    near = inside & (dc <= 1.0)
    city_ratio = float((R[near & CITY].sum() / T[near & CITY].sum()) / (R[near & ~CITY].sum() / T[near & ~CITY].sum())) \
        if (near & CITY).any() and (near & ~CITY).any() else 1.0
    p_dart = None
    if dub is not None and dart_st is not None:
        if demo_run:
            all_dub = dart_st.assign(is_target=True)
        else:   # every station in the box, so homes nearer another line are not counted
            x0, y0, x1, y1 = BOX_DUBLIN_NE
            box = stations[stations["lon"].between(x0 - 0.05, x1 + 0.05) & stations["lat"].between(y0 - 0.05, y1 + 0.05)]
            box = box.assign(key=box["name"].map(lambda x: "".join(str(x).lower().split())))
            tgt = set(dart_st["name"].map(lambda x: "".join(str(x).lower().split())))
            all_dub = box.assign(is_target=box["key"].map(lambda k: any(k.startswith(t) for t in tgt))).drop(columns="key")
        dd, idd = M.nearest(dub, all_dub)
        is_dart = all_dub["is_target"].astype(bool).to_numpy()[idd] & (dd < MAX_KM)
        p_d = M.curve(dub["travellers"].to_numpy()[is_dart], dub["rail"].to_numpy()[is_dart], dd[is_dart])
        p_dart = {"county": p_d, "city": p_d * min(city_ratio, 1.0)}
        tabs.append(M.curve_table(dub["travellers"].to_numpy()[is_dart], dub["rail"].to_numpy()[is_dart],
                                  dd[is_dart], "Dublin DART suburbs"))
    curve_tab = pd.concat(tabs, ignore_index=True)
    print(curve_tab[["curve", "band", "small_areas", "rail_share_pct"]].round(2).to_string(index=False))

    print("3. Leave-one-station-out check (Cork)")
    lo = M.leave_one_out(cork, cork_st)
    lo2 = M.leave_one_out(cork, cork_st, split=True)
    lo["predicted_split"] = lo2["predicted_rail"].to_numpy()
    lo["error_pct"] = 100 * (lo["predicted_rail"] - lo["actual_rail"]) / lo["actual_rail"].replace(0, np.nan)
    lo["error_split_pct"] = 100 * (lo["predicted_split"] - lo["actual_rail"]) / lo["actual_rail"].replace(0, np.nan)
    print(lo.round(1).to_string(index=False))
    corr = float(np.corrcoef(lo["actual_rail"], lo["predicted_rail"])[0, 1]) if len(lo) > 2 else float("nan")
    towns = lo[lo["station"].str.lower() != "cork"]

    print("4. New stations")
    rch = M.reach(cork, new, cork_st)
    e_cork = M.extra_commuters(cork, new, cork_st, p_cork)
    g_lo, g_hi = M.growth_2040()
    est = pd.DataFrame({"station": new["station"], "cork_2022": e_cork.to_numpy()})
    boot = M.bootstrap_extras(cork, new, cork_st, T[inside], R[inside], dc[inside], N_BOOT, rng, CITY[inside])
    est["cork_2022_low"], est["cork_2022_high"] = boot["low"].to_numpy(), boot["high"].to_numpy()
    if p_dart is not None:
        est["dart_2022"] = M.extra_commuters(cork, new, cork_st, p_dart).to_numpy()
    else:
        est["dart_2022"] = np.nan
    est["cork_2040_low"], est["cork_2040_high"] = est["cork_2022"] * g_lo, est["cork_2022"] * g_hi
    est["dart_2040_low"], est["dart_2040_high"] = est["dart_2022"] * g_lo, est["dart_2022"] * g_hi
    sens = M.location_sensitivity(cork, new, cork_st, p_dart if p_dart is not None else p_cork, N_SHIFT, SHIFT_M, rng)
    out = new[["station", "line", "confidence"]].merge(rch, on="station").merge(est, on="station").merge(sens, on="station")
    print(out[["station", "pop_1km", "car_commuters_1km", "car_commuters_2km", "cork_2022", "dart_2022",
               "dart_2040_high", "top3_by_car_1km_pct"]].round(0).to_string(index=False))

    curve_tab.to_csv(RESULTS / "distance_decay.csv", index=False)
    lo.to_csv(RESULTS / "leave_one_out.csv", index=False)
    out.to_csv(RESULTS / "new_stations.csv", index=False)
    summary = {
        "demo": demo_run, "station_source": st_source,
        "cork_small_areas": int(len(cork)), "cork_travellers": float(cork["travellers"].sum()),
        "cork_rail": float(cork["rail"].sum()), "cork_car": float(cork["car"].sum()),
        "loo_corr": corr, "loo_total_ratio": float(lo["predicted_rail"].sum() / lo["actual_rail"].sum()),
        "loo_median_abs_error_pct": float(lo["error_pct"].abs().median()),
        "loo_towns_median_abs_error_split_pct": float(towns["error_split_pct"].abs().median()),
        "loo_towns_median_abs_error_pct": float(towns["error_pct"].abs().median()),
        "kent_actual": float(lo.loc[lo["station"].str.lower() == "cork", "actual_rail"].sum()),
        "kent_predicted_single": float(lo.loc[lo["station"].str.lower() == "cork", "predicted_rail"].sum()),
        "kent_predicted_split": float(lo.loc[lo["station"].str.lower() == "cork", "predicted_split"].sum()),
        "loo_median_abs_error_split_pct": float(lo["error_split_pct"].abs().median()),
        "loo_corr_split": float(np.corrcoef(lo["actual_rail"], lo["predicted_split"])[0, 1]) if len(lo) > 2 else float("nan"),
        "city_ratio": city_ratio,
        "growth_2040": [g_lo, g_hi], "has_dart": p_dart is not None,
        "dart_small_areas": int(is_dart.sum()) if p_dart is not None else 0,
        "totals": {k: float(out[k].sum()) for k in ["cork_2022", "dart_2022", "dart_2040_low", "dart_2040_high",
                                                     "car_commuters_1km", "car_commuters_2km", "pop_1km", "pop_2km",
                                                     "pop_new_to_rail_1km"]},
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2, default=float))

    print("5. Figures and report")
    C.curves(curve_tab, FIGS / "1_distance_decay.png")
    C.validation(lo, FIGS / "2_leave_one_out.png")
    C.reach_bars(rch, FIGS / "3_reach.png")
    C.extras(out.fillna(0), FIGS / "4_extra_commuters.png")
    C.map_(cork, cork_st, new, FIGS / "5_map.png")
    shapes = {} if demo_run else D.load_shapes("cork")
    mapdata.write(cork, shapes, cork_st, new, out, p_cork, p_dart, g_hi)
    report.write()
    print("   docs/index.html and docs/map.html data written")


if __name__ == "__main__":
    main(sys.argv[1:])
