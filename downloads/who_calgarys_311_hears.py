"""
WHO CALGARY'S 311 HEARS - the study's main results in one script
Independent study by Hassan Ali. Not affiliated with The City of Calgary.
https://hassanaliarshad110.github.io/calgary-311/

What it does
  1. Downloads 8 data sets from City of Calgary Open Data (data.calgary.ca), about 1 minute.
  2. Works out the study's main results step by step and prints them next to the published figures.

How to run
  1. Install Python 3 from python.org (Windows: tick "Add Python to PATH").
  2. Save this file, then in a terminal in the same folder:
        py who_calgarys_311_hears.py          (Windows)
        python3 who_calgarys_311_hears.py     (Mac / Linux)
     It installs pandas and numpy the first time if they are missing.

Open Data is live: requests are closed, re-coded or merged as duplicates after the fact, so a few counts
can differ slightly from the published ones (downloaded October 20-21, 2026). The findings do not change.
Each download is saved in a folder called api_responses next to this file; delete it to download again.

Data: City of Calgary Open Data, Open Government Licence - City of Calgary.
"""
import json
import math
import os
import subprocess
import sys
import traceback
import urllib.parse
import urllib.request


def _keep_window_open(kind, value, tb):
    traceback.print_exception(kind, value, tb)
    input('\nSomething went wrong (see above). Press Enter to close...')


sys.excepthook = _keep_window_open
try:
    import numpy as np
    import pandas as pd
except ImportError:
    print('Installing pandas and numpy (one time only)...')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pandas', 'numpy'])
    import numpy as np
    import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'api_responses')
API = 'https://data.calgary.ca/resource/'

# ------------------------------------------------------------------------------------------------------
# Definitions
# ------------------------------------------------------------------------------------------------------
PERIOD = "requested_date>='2024-10-01' AND requested_date<'2026-10-01'"   # Oct 1, 2024 - Sep 30, 2026
NOT_DUPLICATE = "status_description not like 'Duplicate%'"

INFRASTRUCTURE = [                                                        # 21 types: 12 roads, 5 water/sewer, 4 parks
    'Roads - Pothole Maintenance', 'Roads - Streetlight Maintenance', 'Roads - Traffic or Pedestrian Light Repair',
    'Roads - Sidewalk - Curb and Gutter Repair', 'Roads - Roadway Maintenance', 'Roads - Backlane Maintenance',
    'Roads - Debris on Street/Sidewalk/Boulevard', 'Roads - Signs - Missing - Damaged', 'Roads - Snow and Ice Control',
    'Roads - Dead Animal Pick-Up', 'Roads - Pathway Concerns', 'Roads - Pathway Snow and Ice Concerns',
    'WATS - Catch Basin Concerns', 'WATS - Sewage Back-up', 'WATS - Sewer Maintenance', 'WATS - Water Main Break or Leak',
    'WATS - Service and Main Valve Issues',
    'Parks - Tree Concern - GIS', 'Parks - Garbage - GIS', 'Parks - Maintenance - GIS', 'Parks - Infrastructure - GIS']
OTHER_STUDY_TYPES = [                                                     # the other 9 of the 30 common types
    'Corporate - Graffiti Concerns', 'Corporate - Encampment Concerns', 'Bylaw - Snow and Ice on Sidewalk',
    'Bylaw - Long Grass - Weeds Infraction', 'Bylaw - Material on Public Property', 'WRS - Cart Management',
    'WRS - Waste - Residential', 'WRS - Recycling - Blue Cart', 'WRS - Compost - Green Cart']
IN_STUDY_TYPES = 'service_name in(' + ','.join("'" + s + "'" for s in INFRASTRUCTURE + OTHER_STUDY_TYPES) + ')'
DAYS = 'date_diff_d(closed_date,requested_date)'

QUERIES = {   # name: (dataset id, query)
    'by_service': ('iahh-g8bj', {          # 311 requests by community and type
        '$select': 'comm_code,service_name,count(*) as n',
        '$where': f'{PERIOD} AND {NOT_DUPLICATE} AND {IN_STUDY_TYPES}', '$group': 'comm_code,service_name'}),
    'by_channel': ('iahh-g8bj', {          # 311 requests by community and channel (App, Web, Other)
        '$select': 'comm_code,source,count(*) as n',
        '$where': f'{PERIOD} AND {NOT_DUPLICATE}', '$group': 'comm_code,source'}),
    'closed': ('iahh-g8bj', {              # closed requests: how many closed within 7 days, by type and year
        '$select': f'comm_code,service_name,date_extract_y(requested_date) as y,count(*) as n,'
                   f'sum(case({DAYS}<=7,1,true,0)) as w7',
        '$where': f"{PERIOD} AND status_description='Closed' AND {IN_STUDY_TYPES}",
        '$group': 'comm_code,service_name,y'}),
    'centrepoints': ('iahh-g8bj', {        # each community's 311 location point
        '$select': 'comm_code,comm_name,latitude,longitude,count(*) as n',
        '$where': "requested_date>='2025-01-01' AND requested_date<'2026-10-01'",
        '$group': 'comm_code,comm_name,latitude,longitude'}),
    'census_pop': ('f9wk-wej9', {          # 2021 Census population by community
        '$select': 'community_code,total_pop_household'}),
    'equity': ('7g5f-dkmi', {              # Calgary Equity Index: income, renters, no knowledge of English, by area
        '$select': 'area_id,attribute,value', '$where': "area_type='CSA' AND category='Demographic'"}),
    'equity_areas': ('7g5f-dkmi', {        # Calgary Equity Index area outlines
        '$select': 'area_id,multipolygon',
        '$where': "area_type='CSA' AND category='Demographic' AND attribute='Renter'"}),
    'first_year': ('jtpc-xgsh', {          # first census year each community had 500+ residents (community age)
        '$select': 'comm_code,min(census_year) as first_year', '$where': 'population>=500', '$group': 'comm_code'}),
}


def get(name):
    """Download one data set (or reuse the saved copy) and return it as a list of rows."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name + '.json')
    if not os.path.exists(path):
        dataset, query = QUERIES[name]
        url = API + dataset + '.json?' + urllib.parse.urlencode(dict(query, **{'$limit': 50000}))
        with urllib.request.urlopen(url, timeout=300) as r:
            data = r.read()
        with open(path, 'wb') as f:
            f.write(data)
    with open(path, encoding='utf-8') as f:
        rows = json.load(f)
    print(f'  {name:14s} {len(rows):6,} rows')
    return rows


def inside(lon, lat, multipolygon):
    """Is the point inside the area? (even-odd rule over every ring)"""
    hit = False
    for polygon in multipolygon['coordinates']:
        for ring in polygon:
            j = len(ring) - 1
            for i in range(len(ring)):
                (xi, yi), (xj, yj) = ring[i][:2], ring[j][:2]
                if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                    hit = not hit
                j = i
    return hit


def step(title):
    print('\n' + title + '\n' + '-' * len(title))


# ------------------------------------------------------------------------------------------------------
print('Downloading from City of Calgary Open Data...')
D = {name: pd.DataFrame(get(name)) for name in QUERIES}

# ------------------------------------------------------------------------------------------------------
step('1. Communities: 500+ residents in the 2021 Census, inside a Calgary Equity Index area')
pop = D['census_pop'].rename(columns={'community_code': 'comm', 'total_pop_household': 'pop'})
pop['pop'] = pd.to_numeric(pop['pop'])

pts = D['centrepoints'].dropna(subset=['comm_code']).rename(columns={'comm_code': 'comm'})
pts['n'] = pd.to_numeric(pts['n'])
pts = pts.sort_values('n', ascending=False, kind='stable').drop_duplicates('comm')   # most-used point
pts['lat'] = pd.to_numeric(pts['latitude'])
pts['lon'] = pd.to_numeric(pts['longitude'])

areas = list(zip(D['equity_areas']['area_id'], D['equity_areas']['multipolygon']))
pts['area'] = [next((a for a, mp in areas if inside(lon, lat, mp)), None) if lat == lat else None
               for lat, lon in zip(pts['lat'], pts['lon'])]

eq = D['equity'].assign(value=lambda d: pd.to_numeric(d['value']))
eq = eq.pivot_table(index='area_id', columns='attribute', values='value', aggfunc='first')
eq = eq[['Median Income', 'Renter', 'No English Knowledge']].rename(
    columns={'Median Income': 'income', 'Renter': 'renter', 'No English Knowledge': 'noeng'})

K = pop.merge(pts[['comm', 'lat', 'lon', 'area']], on='comm').dropna(subset=['area', 'pop'])
K = K[K['pop'] >= 500].merge(eq, left_on='area', right_index=True)
K['dist_km'] = np.hypot((K['lat'] - 51.0447) * 111, (K['lon'] + 114.0719) * 111 * math.cos(math.radians(51)))
print(f'Communities: {len(K)}   Residents: {int(K["pop"].sum()):,}   (published: 195 and 1,279,690)')

# ------------------------------------------------------------------------------------------------------
step('2. Infrastructure reports per 1,000 residents a year')
req = D['by_service'].assign(n=lambda d: pd.to_numeric(d['n'])).rename(columns={'comm_code': 'comm'})
infra = req[req['service_name'].isin(INFRASTRUCTURE)].groupby('comm')['n'].sum().rename('infra')
K = K.merge(infra, on='comm', how='left').fillna({'infra': 0})
K['rate'] = K['infra'] / K['pop'] * 1000 / 2                              # two years
print(f'Infrastructure reports: {int(K["infra"].sum()):,}   '
      f'({K["infra"].sum() / K["pop"].sum() * 500:.1f} per 1,000 residents a year)')

# ------------------------------------------------------------------------------------------------------
step('3. Raw gap: four equal groups of communities by share with no knowledge of English')
K = K.sort_values('income')
K['group'] = pd.qcut(K['noeng'].rank(method='first'), 4, labels=[1, 2, 3, 4]).astype(int)
g = K.groupby('group').agg(share_no_english=('noeng', 'mean'), infra=('infra', 'sum'), pop=('pop', 'sum'))
g['per_1000_a_year'] = (g['infra'] / g['pop'] * 500).round(1)
print(g[['per_1000_a_year']].rename(index={1: '1 fewest non-English', 4: '4 most non-English'}).to_string())
print(f'Raw gap: {(1 - g.loc[4, "per_1000_a_year"] / g.loc[1, "per_1000_a_year"]) * 100:.1f}% fewer reports'
      f'   (published: 39.3%)')

# ------------------------------------------------------------------------------------------------------
step('4. Like-for-like: same income, renters, distance from downtown and community age')
first = D['first_year'].dropna(subset=['comm_code']).rename(columns={'comm_code': 'comm'})
first['first_year'] = pd.to_numeric(first['first_year'])
K = K.merge(first, on='comm', how='left')
K['age_yrs'] = 2025 - K['first_year']                       # the census series starts in 1968
K['by_1968'] = (K['first_year'] <= 1968).astype(float)
M = K.dropna(subset=['age_yrs'])
X = np.column_stack([np.ones(len(M)), np.log(M['income']), M['renter'], M['noeng'], M['dist_km'],
                     M['age_yrs'], M['by_1968']])
w = np.sqrt(M['pop'].values)                                # bigger communities count more
b = np.linalg.lstsq(X * w[:, None], np.log(M['rate'].values + 1) * w, rcond=None)[0]
print(f'Communities in the model: {len(M)}   (published: 192)')
print(f'A community where 5% have no knowledge of English, compared with one where 1% do: '
      f'{(math.exp(4 * b[3]) - 1) * 100:.1f}%   (published: -22.7%)')

# ------------------------------------------------------------------------------------------------------
step('5. Response: share closed within 7 days, compared with the citywide pace for the same requests')
c = D['closed'].rename(columns={'comm_code': 'comm'})
for col in ['n', 'w7']:
    c[col] = pd.to_numeric(c[col])
c = c[c['comm'].isin(K['comm'])]
city = c.groupby(['service_name', 'y'])[['n', 'w7']].sum()
c = c.merge((city['w7'] / city['n']).rename('city_share'), on=['service_name', 'y'])
c['expected_w7'] = c['n'] * c['city_share']
s = c.merge(K[['comm', 'group']], on='comm').groupby('group')[['w7', 'expected_w7', 'n']].sum()
s['closed_in_7_days_%'] = (s['w7'] / s['n'] * 100).round(1)
s['speed_index'] = (s['w7'] / s['expected_w7'] * 100).round(1)
print(s[['closed_in_7_days_%', 'speed_index']].rename(index={1: '1 fewest non-English', 4: '4 most non-English'})
      .to_string())
print('100 = exactly the citywide pace.   (published speed index: 98.6 to 100.9)')

# ------------------------------------------------------------------------------------------------------
step('6. Requests made through the 311 app')
ch = D['by_channel'].assign(n=lambda d: pd.to_numeric(d['n'])).rename(columns={'comm_code': 'comm'})
ch = ch.merge(K[['comm', 'group']], on='comm')
app = ch[ch['source'] == 'App'].groupby('group')['n'].sum() / ch.groupby('group')['n'].sum() * 100
print(f'Fewest non-English: {app[1]:.1f}%   Most non-English: {app[4]:.1f}%   (published: 23.4% and 18.6%)')
print(f'All non-duplicate requests in the study communities: {int(ch["n"].sum()):,}   (published: 809,528)')

print('\nDone. Full method, data package and the complete analysis code (14 model versions, bootstrap range):')
print('https://hassanaliarshad110.github.io/calgary-311/method.html')
input('\nPress Enter to close...')
