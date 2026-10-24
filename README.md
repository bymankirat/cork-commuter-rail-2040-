# Cork Commuter Rail 2040: who will the eight new stations reach?

Iarnród Éireann's **Cork Area Commuter Rail** programme plans eight new stations (Blackpool/Kilbarry,
Monard, Blarney/Stoneview, Tivoli, Dunkettle, Ballynoe, Carrigtwohill West, Water-Rock) and a service
every 10 minutes on Cork's three commuter lines. The programme gives no forecast per station. This project
uses **Census 2022 data for every Small Area** to answer three questions:

1. **Reach.** How many people, and how many car commuters, live within 1 km and 2 km of each proposed station?
2. **Distance-decay.** How fast does rail use fall with distance from a station, in Cork today and around
   frequent DART stations in north-east Dublin (an upper analogue for a 10-minute service)?
3. **Extra rail commuters.** How many more people would take the train to work from each new station,
   with today's service and a DART-like one, for 2022 and 2040 population?

> Independent analysis. Not an Iarnród Éireann or NTA publication.

## Design choices

* **Validated before use.** The Cork curve is tested by leaving each existing station out of the fit and
  predicting its rail commuters.
* **Uncertainty shown, not hidden.** 95% intervals from resampling Small Areas; station positions are
  approximate, so each is moved at random by up to 600 m, 300 times, to show how much rankings depend on it.
* **Each home counted once**, for its nearest proposed station, so overlapping catchments are not double counted.
* **Outside figures carry their source** in `src/config.py` (CMATS 2040 growth, CSO Cork population).

## Run it

```bash
pip install -r requirements.txt
python tests/run_tests.py      # offline, about a second
python run_pipeline.py         # downloads Census 2022 Small Areas and station positions, then everything else
python run_pipeline.py --demo  # synthetic data, offline
```

Report: `docs/index.html`, interactive map: `docs/map.html` (Leaflet, OpenStreetMap). Both publish with GitHub Pages from `/docs`; open them locally in a browser too.

## Layout

```
run_pipeline.py        data -> curves -> validation -> new-station estimates -> figures -> report
data/new_stations.csv  proposed stations, approximate positions (edit when drawings are available)
src/config.py          settings, study areas, sources and outside figures
src/data.py            Census Hub and Irish Rail downloads, polygon centroids
src/model.py           distances, curves, leave-one-out, reach, extra commuters, bootstrap, location test
src/charts.py          figures
src/report.py          docs/index.html, every number read from results/
tests/run_tests.py     offline tests with known answers
```

## Data

CSO Census 2022 Small Area Population Statistics (Theme 11, via the Census Hub feature service);
Iarnród Éireann real-time API station list; Iarnród Éireann CACR programme page; NTA Cork Metropolitan
Area Transport Strategy (2020); CSO Census 2022 summary results for Cork.

Mankirat Singh · [Portfolio](https://bymankirat.github.io/myportfolio/) · [LinkedIn](https://linkedin.com/in/mankirat-singh-694440177)
