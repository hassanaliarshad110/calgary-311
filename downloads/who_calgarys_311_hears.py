"""
WHO CALGARY'S 311 HEARS - the whole study, step by step
Independent study by Hassan Ali. Not affiliated with The City of Calgary.
https://hassanaliarshad110.github.io/calgary-311/

What it does
  Downloads 8 data sets from City of Calgary Open Data (data.calgary.ca, about 1 minute), then works out
  every main result of the study in 12 numbered steps, printing each next to the published figure.

How to run
  Whole script:   install Python 3 from python.org (Windows: tick "Add Python to PATH"), then
                     py who_calgarys_311_hears.py          (Windows; or double-click the file)
                     python3 who_calgarys_311_hears.py     (Mac / Linux)
                  It installs pandas and numpy the first time if they are missing.
  Block by block: open this file in VS Code (with the Python extension) or Spyder. Each block starts with
                  "# %%"; click "Run Cell" above a block to run just that step.
  As a notebook:  open who_calgarys_311_hears_step_by_step.ipynb (same code, with notes) in Jupyter,
                  VS Code or Google Colab (colab.research.google.com > File > Upload notebook).

Open Data is live: requests are closed, re-coded or merged as duplicates after the fact, so a few counts
can differ slightly from the published ones (downloaded October 20-21, 2026). The findings do not change.
Each download is saved in a folder called api_responses; delete it to download again.

Data: City of Calgary Open Data, Open Government Licence - City of Calgary.
"""

# %%
import sys
import traceback


def _keep_window_open(kind, value, tb):
    """When the script is double-clicked on Windows, keep the window open if something goes wrong."""
    traceback.print_exception(kind, value, tb)
    input('\nSomething went wrong (see above). Press Enter to close...')


if sys.stdin and sys.stdin.isatty():
    sys.excepthook = _keep_window_open


# %% [markdown]
# ## Setup: the tools
# pandas holds the tables, numpy does the arithmetic. Everything else comes with Python.

# %%
import json
import math
import os
import subprocess
import sys
import urllib.parse
import urllib.request

try:
    import numpy as np
    import pandas as pd
except ImportError:
    print('Installing pandas and numpy (one time only)...')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pandas', 'numpy'])
    import numpy as np
    import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
CACHE = os.path.join(HERE, 'api_responses')
API = 'https://data.calgary.ca/resource/'


# %% [markdown]
# ## Definitions: period, duplicates and the 21 infrastructure request types
# Two years, October 1, 2024 to September 30, 2026. Requests the City marked as duplicates are left out.
# "Infrastructure reports" are the 21 request types about public infrastructure: 12 roads, 5 water and sewer and
# 4 parks. The other 9 common types (bylaw, graffiti, encampments, waste carts) are downloaded but not in the main
# measure. Each query below asks Open Data for counts only, so the downloads are small.

# %%
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


# %% [markdown]
# ## Helpers: download, map lookup and the fair-comparison model
# * `get` downloads one data set from Open Data, or reuses the saved copy.
# * `inside` checks whether a point falls inside a map area (used to give each community its Equity Index area).
# * `wls` is the fair-comparison model: a multiple regression, weighted by population so bigger communities count
#   more, on the log of the reporting rate. It also gives a cluster-robust t-value, which allows for communities in
#   the same area sharing the same Census figures.

# %%
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


FACTORS = ['log_income', 'renter', 'noeng', 'dist_km', 'age_yrs', 'by_1968']


def wls(df):
    """Population-weighted least squares on log(rate + 1). Returns coefficients, t, cluster-robust t and R-squared."""
    X = np.column_stack([np.ones(len(df))] + [df[f].values for f in FACTORS])
    y = np.log(df['rate'].values + 1)
    w = np.sqrt(df['pop'].values)                           # bigger communities count more
    Xw, yw = X * w[:, None], y * w
    b = np.linalg.lstsq(Xw, yw, rcond=None)[0]
    res = y - X @ b
    n, k = X.shape
    bread = np.linalg.inv(Xw.T @ Xw)
    se = np.sqrt(np.diag(bread * (w ** 2 * res ** 2).sum() / (n - k)))
    meat = np.zeros((k, k))                                 # cluster-robust (CR1): areas as clusters
    for a in df['area'].unique():
        m = (df['area'] == a).values
        u = (Xw[m] * (res[m] * w[m])[:, None]).sum(0)
        meat += np.outer(u, u)
    g = df['area'].nunique()
    se_cl = np.sqrt(np.diag(bread @ meat @ bread * g / (g - 1) * (n - 1) / (n - k)))
    r2 = 1 - (w ** 2 * res ** 2).sum() / (w ** 2 * (y - np.average(y, weights=w ** 2)) ** 2).sum()
    return pd.DataFrame({'coef': b, 't': b / se, 't_cluster': b / se_cl}, index=['const'] + FACTORS), r2


def effect(b_noeng):
    """Difference in reports between a community where 5% have no English and one where 1% do."""
    return (math.exp(4 * b_noeng) - 1) * 100


def step(title):
    print('\n' + title + '\n' + '-' * len(title))


# %% [markdown]
# ## Download the data
# Eight small downloads from City of Calgary Open Data: 311 counts by community and type, by channel, and closed
# within 7 days; each community's location; the 2021 Census population; the Calgary Equity Index (income, renters,
# language) with its area outlines; and the first Census year each community had 500 or more residents.

# %%
print('Downloading from City of Calgary Open Data...')
D = {name: pd.DataFrame(get(name)) for name in QUERIES}


# %% [markdown]
# ## Step 1. Which communities are in the study
# Communities with 500 or more residents in the 2021 Census. Each is placed in its Calgary Equity Index area (using
# the point where most of its 311 requests are located), which gives it the area's median income, share of renters
# and share of residents with no knowledge of English. Distance from downtown is measured from City Hall.
# **Published: 195 communities, 1,279,690 residents.**

# %%
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

K = pop.merge(pts[['comm', 'comm_name', 'lat', 'lon', 'area']], on='comm').dropna(subset=['area', 'pop'])
K = K[K['pop'] >= 500].merge(eq, left_on='area', right_index=True)
K['dist_km'] = np.hypot((K['lat'] - 51.0447) * 111, (K['lon'] + 114.0719) * 111 * math.cos(math.radians(51)))
print(f'Communities: {len(K)}   Residents: {int(K["pop"].sum()):,}   (published: 195 and 1,279,690)')


# %% [markdown]
# ## Step 2. Infrastructure reports per 1,000 residents a year
# Each community's infrastructure reports over the two years, divided by its 2021 residents, so large and small
# communities can be compared fairly.

# %%
step('2. Infrastructure reports per 1,000 residents a year')
req = D['by_service'].assign(n=lambda d: pd.to_numeric(d['n'])).rename(columns={'comm_code': 'comm'})
infra = req[req['service_name'].isin(INFRASTRUCTURE)].groupby('comm')['n'].sum().rename('infra')
K = K.merge(infra, on='comm', how='left').fillna({'infra': 0})
K['rate'] = K['infra'] / K['pop'] * 1000 / 2                              # two years
print(f'Infrastructure reports: {int(K["infra"].sum()):,}   '
      f'({K["infra"].sum() / K["pop"].sum() * 500:.1f} per 1,000 residents a year)')


# %% [markdown]
# ## Step 3. Four groups of communities (the raw gap)
# Communities sorted by the share of residents who can't hold a conversation in English and split into four
# groups of about 49. This shows *that* there is a difference, not why: the "most" group also has lower incomes.
# **Published: 90.0, 86.7, 69.8, 54.6 per 1,000; 39.3% fewer.**

# %%
step('3. Raw gap: four equal groups of communities by share with no knowledge of English')
K = K.sort_values('income')
K['group'] = pd.qcut(K['noeng'].rank(method='first'), 4, labels=[1, 2, 3, 4]).astype(int)
g = K.groupby('group').agg(communities=('comm', 'size'), share_no_english=('noeng', 'mean'),
                           infra=('infra', 'sum'), pop=('pop', 'sum'))
g['per_1000_a_year'] = (g['infra'] / g['pop'] * 500).round(1)
print(g[['communities', 'per_1000_a_year']].rename(index={1: '1 fewest', 2: '2 fewer', 3: '3 more', 4: '4 most'})
      .to_string())
print(f'Raw gap: {(1 - g.loc[4, "infra"] / g.loc[4, "pop"] / (g.loc[1, "infra"] / g.loc[1, "pop"])) * 100:.1f}% fewer reports'
      f'   (published: 39.3%)')


# %% [markdown]
# ## Step 4. Communities of similar age
# Older communities have older roads and pipes, so they have more to report. Here only communities first settled
# (500+ residents) between 1975 and 2000 are kept, so infrastructure is of broadly similar age, and they are split
# into three groups of 21. **Published: 63 communities; 59.7, 51.7, 44.6 per 1,000; about 25% fewer.**

# %%
step('4. Communities first settled 1975-2000, three groups by share with no knowledge of English')
first = D['first_year'].dropna(subset=['comm_code']).rename(columns={'comm_code': 'comm'})
first['first_year'] = pd.to_numeric(first['first_year'])
K = K.merge(first, on='comm', how='left')
S = K[(K['first_year'] >= 1975) & (K['first_year'] <= 2000)].copy()
S['third'] = pd.qcut(S['noeng'].rank(method='first'), 3, labels=[1, 2, 3]).astype(int)
t = S.groupby('third').agg(communities=('comm', 'size'), infra=('infra', 'sum'), pop=('pop', 'sum'))
t['per_1000_a_year'] = (t['infra'] / t['pop'] * 500).round(1)
print(t[['communities', 'per_1000_a_year']].rename(index={1: '1 fewest', 2: '2 middle', 3: '3 most'}).to_string())
print(f'Communities: {len(S)}   Gap: {(1 - t.loc[3, "infra"] / t.loc[3, "pop"] / (t.loc[1, "infra"] / t.loc[1, "pop"])) * 100:.1f}%'
      f' fewer   (published: 63 communities, 25.2%)')


# %% [markdown]
# ## Step 5. Is it income? Income and language side by side
# Communities split at the middle (median) for income and for language. If income were the reason, the rows
# would look alike. **Published: more English speakers 106 (lower income) and 83 (higher); fewer English speakers
# 64 and 53.** This simple table doesn't account for community age; the model in Step 6 does.

# %%
step('5. Income and language: infrastructure reports per 1,000 a year')
K['higher_income'] = np.where(K['income'] > K['income'].median(), 'Higher income', 'Lower income')
K['english'] = np.where(K['noeng'] <= K['noeng'].median(), 'More English speakers', 'Fewer English speakers')
box = K.groupby(['english', 'higher_income']).agg(infra=('infra', 'sum'), pop=('pop', 'sum'), n=('comm', 'size'))
box['rate'] = (box['infra'] / box['pop'] * 500).round(0).astype(int)
print(box['rate'].unstack().loc[['More English speakers', 'Fewer English speakers'],
                                ['Lower income', 'Higher income']].to_string())
print('Communities in each box:')
print(box['n'].unstack().loc[['More English speakers', 'Fewer English speakers'],
                             ['Lower income', 'Higher income']].to_string())
print('(published: 106, 83 / 64, 53)')


# %% [markdown]
# ## Step 6. The fair-comparison model
# One multiple regression over all communities with an age figure. It holds income, renters, distance from downtown
# and community age equal, and separates the link with language. Community age is the years since the community
# first had 500 residents; `by_1968` marks communities that already existed when the Census series starts.
# The result is put in plain terms: a community where 5 in 100 residents have no knowledge of English, compared
# with an otherwise identical one where 1 in 100 don't. **Published: 192 communities; -22.7%; t = -4.28 (cluster-robust
# -3.92); R-squared 0.617.**

# %%
step('6. Fair-comparison model: same income, renters, distance from downtown and community age')
K['age_yrs'] = 2025 - K['first_year']                       # the census series starts in 1968
K['by_1968'] = (K['first_year'] <= 1968).astype(float)
K['log_income'] = np.log(K['income'])
M = K.dropna(subset=['age_yrs']).reset_index(drop=True)
coefs, r2 = wls(M)
print(coefs.round(4).to_string())
print(f'Communities in the model: {len(M)}   R-squared: {r2:.3f}   (published: 192 and 0.617)')
print(f'5% vs 1% with no knowledge of English: {effect(coefs.loc["noeng", "coef"]):.1f}%   (published: -22.7%)')


# %% [markdown]
# ## Step 7. How sure? 1,000 re-runs (bootstrap)
# The model is run again 1,000 times, each time on a random re-draw of the Equity Index areas (with their
# communities), to see how much the result moves. **Published: in 95% of re-runs the gap was between 9% and 33%.**

# %%
step('7. Bootstrap: 1,000 re-runs on random re-draws of the areas')
rng = np.random.default_rng(42)
area_list = M['area'].unique()
runs = []
for _ in range(1000):
    pick = rng.choice(area_list, len(area_list), replace=True)
    sample = pd.concat([M[M['area'] == a] for a in pick], ignore_index=True)
    runs.append(effect(wls(sample)[0].loc['noeng', 'coef']))
runs = np.array(runs)
lo, hi = np.percentile(runs, [2.5, 97.5])
print(f'95% of re-runs: {-hi:.1f}% to {-lo:.1f}% fewer reports   (published: 9% to 33%)')
print(f'Re-runs where the gap stayed below zero: {(runs < 0).mean() * 100:.1f}%')


# %% [markdown]
# ## Step 8. Every request type
# Does the gap come from one or two kinds of request, or from many? Each of the 21 types is compared between the
# group with the most residents who can't speak English and the group with the fewest (raw rates, as in Step 3).
# A gap across nearly every type, including streetlights, which the City learns about mainly from residents'
# reports, points to a difference in reporting. **Published: lower in 20 of 21 types.**

# %%
step('8. Each infrastructure request type: most vs fewest non-English group (raw)')
r = req[req['service_name'].isin(INFRASTRUCTURE)].merge(K[['comm', 'group']], on='comm')
by_type = r[r['group'].isin([1, 4])].pivot_table(index='service_name', columns='group', values='n', aggfunc='sum')
by_type = by_type.fillna(0)
group_pop = K.groupby('group')['pop'].sum()
for gq in (1, 4):
    by_type[gq] = by_type[gq] / group_pop[gq] * 500
by_type['difference_%'] = ((by_type[4] / by_type[1] - 1) * 100).round(1)
print(by_type['difference_%'].sort_values().to_string())
print(f'Lower in the most non-English group: {(by_type["difference_%"] < 0).sum()} of {len(by_type)} types'
      f'   (published: 20 of 21)')


# %% [markdown]
# ## Step 9. Does the City respond equally fast?
# For each request, the share closed within 7 days is compared with the citywide share for the same request type in
# the same year, so a group with more slow request types isn't counted as slower. 100 means exactly the citywide pace.
# "Closed" is the City's administrative status. **Published: every group within 1.5% (98.6 to 100.9).**

# %%
step('9. Closed within 7 days, compared with the citywide pace for the same requests')
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
print(s[['closed_in_7_days_%', 'speed_index']].rename(index={1: '1 fewest', 2: '2 fewer', 3: '3 more', 4: '4 most'})
      .to_string())
print('100 = exactly the citywide pace.   (published speed index: 98.6 to 100.9)')


# %% [markdown]
# ## Step 10. Requests made through the 311 app
# **Published: 23.4% in the group with the fewest residents who can't speak English, 18.6% in the group with the
# most; 809,528 requests in the 195 study communities.**

# %%
step('10. Requests made through the 311 app')
ch = D['by_channel'].assign(n=lambda d: pd.to_numeric(d['n'])).rename(columns={'comm_code': 'comm'})
ch = ch.merge(K[['comm', 'group']], on='comm')
app = ch[ch['source'] == 'App'].groupby('group')['n'].sum() / ch.groupby('group')['n'].sum() * 100
print(f'Fewest non-English: {app[1]:.1f}%   Most non-English: {app[4]:.1f}%   (published: 23.4% and 18.6%)')
print(f'All non-duplicate requests in the study communities: {int(ch["n"].sum()):,}   (published: 809,528)')


# %% [markdown]
# ## Step 11. Ward 5 communities against similar communities
# Each community's reports compared with what is typical for communities with the same income, share of renters,
# distance from downtown and age: the Step 6 model without language, scaled so the citywide total matches.
# This uses 2021 population, as in the original study. **Published (Report to the City): Taradale -34%,
# Martindale -27%, Falconridge +3%.** The Ward 5 report adjusts for growth since 2021 (Taradale -32%, Martindale -26%).

# %%
step('11. Ward 5 communities against similar communities (2021 population)')
SIMILAR = ['log_income', 'renter', 'dist_km', 'age_yrs', 'by_1968']      # everything except language
X = np.column_stack([np.ones(len(M))] + [M[f].values for f in SIMILAR])
w = np.sqrt(M['pop'].values)
b = np.linalg.lstsq(X * w[:, None], np.log(M['rate'].values + 1) * w, rcond=None)[0]
typical = np.exp(X @ b) - 1
typical = typical * np.average(M['rate'].values / typical, weights=M['pop'].values)   # match the citywide level
M['vs_similar_%'] = (M['rate'] / typical - 1) * 100
WARD5 = ['TAR', 'MRT', 'SKR', 'CAS', 'RSN', 'SAD', 'FAL', 'CSC', 'CNS']
w5 = M[M['comm'].isin(WARD5)].sort_values('vs_similar_%')
cols = {'comm_name': 'community', 'pop': 'residents_2021', 'noeng': 'no_english_%', 'rate': 'per_1000_a_year',
        'vs_similar_%': 'vs_similar_%'}
w5['pop'] = w5['pop'].astype(int)
w5['comm_name'] = w5['comm_name'].str.title()
print(w5.rename(columns=cols)[list(cols.values())].round(1).to_string(index=False))
print('(published, 2021 population: Taradale -34%, Martindale -27%)')


# %% [markdown]
# ## Step 12. What the results show, and what they don't
# **They show** which communities 311 hears less from: a gap that holds in every check, in nearly every request
# type, and among communities of similar age; and that once a request is made, the City closes it at the same pace
# in every group.
#
# **They don't show** the cause (language, being newer to Canada and other factors go together); whether those
# communities have fewer problems, or how many problems City inspections already catch without a report (City
# inspection data could test both); or whether the residents who can't speak English are themselves the ones not
# reporting, because the language figures are for areas, not people.
#
# Full method, the 14 model versions and the reports: https://hassanaliarshad110.github.io/calgary-311/method.html

# %%
print('\nDone. Full method, data package and reports: https://hassanaliarshad110.github.io/calgary-311/method.html')
if sys.stdin and sys.stdin.isatty():
    input('\nPress Enter to close...')
