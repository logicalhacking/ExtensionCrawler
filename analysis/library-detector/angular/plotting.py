import sys
import datetime
from dateutil import parser
from distutils.version import LooseVersion


import numpy as np
from matplotlib import pyplot as plt
import matplotlib.patches as mpatches

def get_cmap(n, name='hsv'):
    '''Returns a function that maps each index in 0, 1, ..., n-1 to a distinct
    RGB color; the keyword argument name must be a standard mpl colormap name.'''
    return plt.cm.get_cmap(name, n)


plt.figure(figsize=(20, 100))

data = {}
with open(sys.argv[1]) as f:
    for line in f.readlines()[0:5000]:
        line = line.strip()
        extid, ts, vers = line.split(",")
        if extid not in data:
            data[extid] = {}
        data[extid][parser.parse(ts).date()] = vers

startdate = datetime.date(year=2017, month=2, day=1)
enddate = datetime.date(year=2018, month=12, day=13)
NOT_IN_STORE = "NO DATA"



converted_data = {}
versions = set()
for extid, tups in data.items():
    days_version_tups = [(0, NOT_IN_STORE)]
    for ts, vers in sorted(tups.items()):
        if vers != "None":
            versions.add(vers)
        #if vers != days_version_tups[-1][1]:
        days_version_tups += [((ts - startdate).days, vers)]
    converted_data[extid] = days_version_tups

converted_data["angular_updates"] = [(0, NOT_IN_STORE)]
version_release = {}
with open(sys.argv[2]) as f:
    for line in f.readlines():
        line = line.strip()
        vers, ts_str = line.split(",")
        ts = parser.parse(ts_str).date()
        version_release[vers] = ts
        if startdate < ts and ts < enddate:
            converted_data["angular_updates"] += [((ts - startdate).days, vers)]

converted_data["angular_updates"].sort()


colors = {}
for i, version in enumerate(sorted(versions, key=version_release.get)):
    #colors[version] = get_cmap(len(versions))(i)
    colors[version] = plt.cm.jet(1. * i / ((len(versions)) - 1))
for version, color in colors.items():
    print(f"{version}: {color}")

bottoms = np.arange(len(converted_data))

sorted_data = sorted(list(converted_data.items()), key=lambda x: min(map(lambda y: y[1], x[1])))

for i in range(len(converted_data.items())):
    extid, tups = sorted_data[i]
    for j in range(len(tups)):
        days, vers = tups[j]
        if j + 1 == len(tups):
            next_days = (enddate - startdate).days
        else:
            next_days = tups[j + 1][0]
        print(f"{extid}: {days}")
        #print(f"{vers} and {colors[vers]}")
        color = "w"
        if vers in colors:
            color = colors[vers]
        plt.bar(days, 0.8, width=next_days - days, bottom=bottoms[i],
                color=color, orientation="horizontal", label=vers, linewidth=1, edgecolor="black")
plt.yticks(bottoms, map(lambda x: x[0], sorted(list(converted_data.items()), key=lambda x: min(map(lambda y: y[1], x[1])))))

patchList = []
for version, color in sorted(colors.items(), key=lambda x: LooseVersion(x[0])):
        data_key = mpatches.Patch(color=color, label=version)
        patchList.append(data_key)

plt.legend(handles=patchList, loc="best", bbox_to_anchor=(1.0, 1.00))


plt.subplots_adjust(right=0.85)
plt.savefig("out.pdf")
