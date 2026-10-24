"""Every setting and every outside figure the results depend on, with its source."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results"
DOCS = ROOT / "docs"
FIGS = DOCS / "figures"
NEW_STATIONS_FILE = ROOT / "data" / "new_stations.csv"

# Census 2022 Small Areas with means of travel to work (CSO Census Hub, ArcGIS feature service)
SA_LAYER = ("https://services-eu1.arcgis.com/BuS9rtTsYEV5C0xh/ArcGIS/rest/services/"
            "CensusHub2022_T11_1_SA/FeatureServer/0/query")
SA_FIELDS = ["GEOGID", "ED_ENGLISH", "LOCAL_AUTHORITY", "T1_1AGETT_Norm",
             "T11_1_FW", "T11_1_BIW", "T11_1_BUW", "T11_1_TDLW", "T11_1_MW", "T11_1_CDW",
             "T11_1_CPW", "T11_1_VW", "T11_1_OTHW", "T11_1_WMFHW", "T11_1_NSW", "T11_1_TW"]
PAGE = 1000

# Study areas, as lon/lat boxes
BOX_CORK = (-8.75, 51.80, -8.10, 52.16)      # Cork metropolitan rail corridors, Mallow to Midleton
BOX_DUBLIN_NE = (-6.25, 53.33, -6.02, 53.47)  # north-east Dublin DART suburbs (no Luas lines)

# Irish Rail real-time API: station names and coordinates
STATIONS_URL = "https://api.irishrail.ie/realtime/realtime.asmx/getAllStationsXML"

# Existing Cork commuter stations (names as in the Irish Rail API)
CORK_STATIONS = ["Cork", "Little Island", "Glounthaune", "Fota", "Carrigaloe", "Rushbrooke",
                 "Cobh", "Carrigtwohill", "Midleton", "Mallow"]
# Approximate positions, used only if the API cannot be reached
CORK_FALLBACK = {
    "Cork": (51.9018, -8.4582), "Little Island": (51.9076, -8.3540), "Glounthaune": (51.9116, -8.3263),
    "Fota": (51.8961, -8.3184), "Carrigaloe": (51.8718, -8.3233), "Rushbrooke": (51.8496, -8.3226),
    "Cobh": (51.8493, -8.2985), "Carrigtwohill": (51.9165, -8.2635), "Midleton": (51.9192, -8.1777),
    "Mallow": (52.1290, -8.6551),
}
# High-frequency analogue: north-east Dublin DART stations, about every 10-15 minutes at peak
DART_ANALOGUE = ["Clontarf Road", "Killester", "Harmonstown", "Raheny", "Kilbarrack", "Howth Junction",
                 "Bayside", "Sutton", "Howth", "Portmarnock", "Malahide"]

# Distance bands (km) for the distance-decay curves
BANDS = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
CATCH_KM = [1.0, 2.0]          # walk (1 km) and short cycle/drive (2 km) catchments
MAX_KM = 5.0                   # beyond this an area is not counted for any station

N_BOOT = 500
N_SHIFT = 300
SHIFT_M = 600                  # station positions are approximate: test moves of up to 600 m
SEED = 7

# Growth to 2040. CMATS (NTA, 2020): Cork's population projected to rise 50-60% by 2040 from a
# 2016 base. Census: Cork (city and county) 542,868 in 2016 and 584,156 in 2022 (CSO).
GROWTH_2016_2040 = (1.50, 1.60)
POP_CORK_2016, POP_CORK_2022 = 542_868, 584_156
SOURCES = {
    "census": "CSO, Census 2022 Small Area Population Statistics, Theme 11 (Census Hub feature service)",
    "stations": "Iarnród Éireann real-time API (station list)",
    "cacr": "Iarnród Éireann, Cork Area Commuter Rail programme page (8 proposed stations)",
    "cmats": "NTA, Cork Metropolitan Area Transport Strategy 2040 (2020): 50-60% population growth by 2040",
    "cso_cork": "CSO, Census 2022 summary results for Cork: 584,156 (2022), up 41,288 from 2016",
}
