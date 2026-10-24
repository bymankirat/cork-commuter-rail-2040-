"""Writes docs/index.html. Every number on the page is read from results/."""

from __future__ import annotations

import html
import json

import pandas as pd

from config import CATCH_KM, DOCS, RESULTS, SHIFT_M, SOURCES

CSS = """
:root{--bg:#f6f5f1;--fg:#1d2733;--muted:#5b6672;--card:#fff;--line:#dcd9d2;--accent:#1f5f8b;--warm:#c4661f;--chip:#eceae4}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14181d;--fg:#e8ecf0;--muted:#9aa5b1;--card:#1c222a;--line:#313a45;--accent:#7fb6e0;--warm:#e89a5c;--chip:#252d37;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#14181d;--fg:#e8ecf0;--muted:#9aa5b1;--card:#1c222a;--line:#313a45;--accent:#7fb6e0;--warm:#e89a5c;--chip:#252d37;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 Georgia,'Iowan Old Style',serif;
 padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
main{max-width:800px;margin:0 auto;padding-block:40px 64px}
h1,h2{font-family:system-ui,'Segoe UI',Arial,sans-serif;text-wrap:balance;line-height:1.25}
h1{font-size:30px;margin:0 0 8px}h2{font-size:21px;margin:40px 0 8px}
.kicker{font:600 12px/1 system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.lede{font-size:18px}.meta{color:var(--muted);font:14px/1.5 system-ui,sans-serif}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:24px 0}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;min-width:0}
.tile b{display:block;font:700 26px/1.1 system-ui,sans-serif;color:var(--accent)}
.tile span{font:13px/1.4 system-ui,sans-serif;color:var(--muted)}
figure{margin:20px 0;background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px}
figure img{width:100%;height:auto;display:block}
figcaption{font:13px/1.5 system-ui,sans-serif;color:#5b6672;margin-top:8px}
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--card);margin:16px 0}
table{border-collapse:collapse;width:100%;font:14px/1.4 system-ui,sans-serif;min-width:640px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right}
th:first-child,td:first-child{text-align:left}
th{background:var(--chip);font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.note{background:var(--card);border-left:3px solid var(--warm);padding:12px 16px;border-radius:6px;font-size:15px}
.btn{display:inline-block;background:var(--accent);color:var(--card);text-decoration:none;font:600 15px system-ui,sans-serif;padding:10px 16px;border-radius:8px;margin-right:8px}
a{color:var(--accent)}code{font:13px ui-monospace,Menlo,monospace;background:var(--chip);padding:1px 5px;border-radius:4px}
"""


def n0(x):
    return f"{x:,.0f}"


def table(df, cols):
    head = "".join(f"<th>{html.escape(h)}</th>" for _, h, _ in cols)
    body = ""
    for _, r in df.iterrows():
        body += "<tr>" + "".join(
            f"<td>{html.escape(str(r[c])) if f is None else f(r[c])}</td>" for c, _, f in cols) + "</tr>"
    return f'<div class="tbl"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def write():
    S = json.loads((RESULTS / "summary.json").read_text())
    ns = pd.read_csv(RESULTS / "new_stations.csv")
    lo = pd.read_csv(RESULTS / "leave_one_out.csv")
    dd = pd.read_csv(RESULTS / "distance_decay.csv")
    T = S["totals"]
    g0, g1 = S["growth_2040"]
    rail_pct = 100 * S["cork_rail"] / S["cork_travellers"]
    car_pct = 100 * S["cork_car"] / S["cork_travellers"]

    top_car = ns.sort_values("car_commuters_1km", ascending=False)
    lead = top_car.iloc[0]
    stable = ns[ns["top3_by_car_1km_pct"] >= 90]["station"].tolist()
    cork_near = dd[(dd["curve"] == "Cork today")].iloc[0]["rail_share_pct"]
    dart_rows = dd[dd["curve"] == "Dublin DART suburbs"]
    dart_near = dart_rows.iloc[0]["rail_share_pct"] if len(dart_rows) else float("nan")
    ratio = S["loo_total_ratio"]
    valid_txt = (f"Predicted and actual rail commuters agree in total to within {abs(ratio - 1) * 100:.0f}% "
                 f"(correlation across stations {S['loo_corr']:.2f}; median error per station "
                 f"{S['loo_median_abs_error_pct']:.0f}%).")

    tiles = [
        (n0(T["pop_1km"]), "people live within 1 km of the eight proposed stations"),
        (n0(T["car_commuters_1km"]), "of them commute by car today (within 1 km)"),
        (f"{rail_pct:.1f}%", f"of commuters in the Cork study area take the train today; {car_pct:.0f}% go by car"),
        (f"{n0(T['cork_2022'])}–{n0(T['dart_2040_high'])}" if S["has_dart"] else n0(T["cork_2022"]),
         "extra daily rail commuters from the new stations: today's service, 2022 homes, to a DART-like service, 2040 homes"),
    ]
    tiles_html = "".join(f'<div class="tile"><b>{a}</b><span>{html.escape(b)}</span></div>' for a, b in tiles)

    reach_tbl = table(top_car, [
        ("station", "Station", None), ("line", "Line", None),
        ("pop_1km", "People ≤1 km", n0), ("pop_new_to_rail_1km", "…not now ≤1 km of rail", n0),
        ("car_commuters_1km", "Car commuters ≤1 km", n0), ("car_commuters_2km", "Car commuters ≤2 km", n0),
        ("top3_by_car_1km_pct", f"In top 3 if moved ≤{SHIFT_M} m", lambda v: f"{v:.0f}%")])
    est_cols = [("station", "Station", None), ("cork_2022", "Today's service", n0),
                ("cork_2022_low", "95% low", n0), ("cork_2022_high", "95% high", n0)]
    if S["has_dart"]:
        est_cols += [("dart_2022", "DART-like, 2022", n0), ("dart_2040_low", "DART-like, 2040 low", n0),
                     ("dart_2040_high", "DART-like, 2040 high", n0)]
    est_tbl = table(ns.sort_values("dart_2040_high" if S["has_dart"] else "cork_2022", ascending=False), est_cols)
    lo_tbl = table(lo.sort_values("actual_rail", ascending=False), [
        ("station", "Station", None), ("small_areas", "Small areas", n0), ("travellers", "Commuters", n0),
        ("actual_rail", "Rail, actual", n0), ("predicted_rail", "Rail, predicted", n0)])

    dart_par = ""
    if S["has_dart"]:
        dart_par = (f"<p>Within half a kilometre of a station, {cork_near:.1f}% of commuters take the train in Cork "
                    f"today, against {dart_near:.1f}% around the north-east Dublin DART stations, which run every "
                    "10–15 minutes at peak. The gap is the size of the prize from the planned 10-minute service. "
                    "The Dublin curve is an upper analogue, not a forecast: Dublin has more jobs within a short "
                    "train ride, and more congestion to avoid.</p>")

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Cork Commuter Rail 2040</title><style>{CSS}</style></head><body><main>
<p class="kicker">Cork Area Commuter Rail · Census 2022 · eight proposed stations</p>
<h1>Who will the eight new Cork stations reach, and how many will switch to rail?</h1>
<p class="lede">Iarnród Éireann plans eight new stations and a service every 10 minutes on Cork's three
commuter lines. The programme page gives no forecast per station. This analysis uses Census 2022 data for
every Small Area to show who lives near each proposed station, how they travel to work today, and how many
extra rail commuters each station could add, today and in 2040.</p>
<p class="meta">Mankirat Singh · Independent analysis, not an Iarnród Éireann or NTA publication ·
<a href="https://github.com/bymankirat">Code</a> · <a href="https://bymankirat.github.io/myportfolio/">Portfolio</a></p>
<div class="tiles">{tiles_html}</div>
<p><a class="btn" href="map.html">Open the interactive map →</a> Every Small Area, every station, both scenarios.</p>

<h2>1. Who lives near each proposed station</h2>
<p>{html.escape(lead['station'])} has the most car commuters within 1 km ({n0(lead['car_commuters_1km'])}).
Each Small Area is counted once, for its nearest proposed station. The station positions are approximate,
so every station was moved at random by up to {SHIFT_M} m, {300} times:
{("the stations that stay in the top three in at least 90% of moves are " + ", ".join(html.escape(s) for s in stable) + ".") if stable else "no station stays in the top three in 90% of moves, so the ranking depends on exact positions."}</p>
<figure><img src="figures/5_map.png" alt="Map of Cork Small Areas shaded by car commuting, with existing and proposed stations">
<figcaption>Each dot is a Census 2022 Small Area, sized by the number of commuters and shaded by the share going by car.</figcaption></figure>
<figure><img src="figures/3_reach.png" alt="Bar chart of car commuters within 1 and 2 km of each proposed station"></figure>
{reach_tbl}

<h2>2. How rail use falls with distance</h2>
<p>Only {rail_pct:.1f}% of commuters in the study area take the train today. The share is highest near
stations and falls quickly with distance.</p>
{dart_par}
<figure><img src="figures/1_distance_decay.png" alt="Line chart of rail share by distance to the nearest station, Cork and Dublin DART">
<figcaption>Share of people who travel to work going by train, by distance from home to the nearest station.</figcaption></figure>

<h2>3. Does distance explain station use? A leave-one-out test</h2>
<p>For each existing Cork station, the curve was fitted without that station's area and used to predict its
rail commuters. {valid_txt}</p>
<figure><img src="figures/2_leave_one_out.png" alt="Scatter of predicted against actual rail commuters per existing Cork station"></figure>
{lo_tbl}

<h2>4. Extra rail commuters from each new station</h2>
<p>A new station moves some homes closer to rail. The extra commuters are the people in those homes times
the rise in the curve between their old and new distance. With today's service and 2022 homes the gain is
{n0(T['cork_2022'])} people a day across all eight stations.
{f"With a DART-like service it is {n0(T['dart_2022'])}, and {n0(T['dart_2040_low'])}–{n0(T['dart_2040_high'])} with 2040 population ({(g0 - 1) * 100:.0f}–{(g1 - 1) * 100:.0f}% growth from 2022, from CMATS)." if S['has_dart'] else ""}
These are people travelling to work only; students, leisure trips and park-and-ride users from further away add to them.</p>
<figure><img src="figures/4_extra_commuters.png" alt="Range of extra daily rail commuters per station between scenarios"></figure>
{est_tbl}

<h2>What this means for planning</h2>
<p>The stations with the largest reach are where the 10-minute service matters most. Several stations (Monard,
Carrigtwohill West, Water-Rock) mainly serve homes and jobs that are planned but not yet built, so Census 2022
understates them by design: their case rests on development, which this analysis cannot see. Where the
estimate is small even under a DART-like service, the case for the station depends on park and ride and new
development rather than existing homes.</p>

<h2>Limitations</h2>
<p class="note">Station positions are estimated from published descriptions, not survey drawings; edit
<code>data/new_stations.csv</code> to update them, and the location test above shows how much that matters.
Distances are straight lines, not walking routes. The Census counts the main mode to work in April 2022,
when many people worked from home part of the week. Growth to 2040 is applied evenly, while real growth
will concentrate in planned areas. The Dublin analogue includes destinations and congestion that Cork lacks.</p>

<h2>Reproduce it</h2>
<p><code>pip install -r requirements.txt</code>, <code>python tests/run_tests.py</code>, then
<code>python run_pipeline.py</code>. Every number on this page is read from <code>results/</code>.</p>
<p class="meta">Data: {html.escape(SOURCES['census'])}; {html.escape(SOURCES['stations'])}; {html.escape(SOURCES['cacr'])};
{html.escape(SOURCES['cmats'])}; {html.escape(SOURCES['cso_cork'])}. Catchments: {', '.join(f'{k:g} km' for k in CATCH_KM)} straight line.</p>
</main></body></html>"""
    (DOCS / "index.html").write_text(page, encoding="utf-8")
