import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from shapely.geometry import LineString
import numpy as np



airports = {
    "EGLL": (51.4706, -0.46194), "LFPG": (49.0128, 2.55), "EHAM": (52.3086, 4.7639),
    "EDDF": (50.0333, 8.5706), "LEMF": (40.4719, -3.5626), "LEBL": (41.2971, 2.0785),
    "EDDM": (48.3538, 11.7861), "LIRF": (41.8003, 12.2389), "EIDW": (53.4213, -6.2701),
    "ESSA": (59.6519, 17.9186), "LPPT": (38.7813, -9.1359), "EDDT": (52.5597, 13.2877),
    "EFHK": (60.3172, 24.9633), "EPWA": (52.1657, 20.9671), "EGPH": (55.95, -3.3727),
    "LROP": (44.5711, 26.085), "LICJ": (38.1108, 13.3133)
}


routes = [
    ("EDDF", "LEMF"), ("EDDF", "LEBL"), ("EDDF", "EDDM"), ("EDDF", "EIDW"),
    ("EDDF", "ESSA"), ("EDDF", "EDDT"), ("EDDF", "EFHK"), ("EDDF", "EPWA"),
    ("EDDF", "EGPH"), ("EDDF", "LROP"), ("EDDF", "LICJ"), ("LEMF", "EDDF"),
    ("LEMF", "LPPT"), ("LEBL", "LEMF"), ("EDDM", "EDDF"), ("EDDM", "LIRF"),
    ("LIRF", "EDDF"), ("EIDW", "EDDF"), ("ESSA", "EDDF"), ("LPPT", "EDDF"),
    ("EDDT", "ESSA"), ("EFHK", "ESSA"), ("EPWA", "LROP"), ("EGPH", "EDDF"),
    ("LROP", "EDDF"), ("LICJ", "LIRF"), ("EGLL", "LFPG"), ("EGLL", "EDDF"),
    ("EGLL", "EIDW"), ("EGLL", "EGPH"), ("LFPG", "EGLL"), ("LFPG", "EDDF"),
    ("LFPG", "LEMF"), ("LFPG", "LEBL"), ("EHAM", "EGLL"), ("EHAM", "LFPG"),
    ("EHAM", "EDDF"), ("EDDF", "EGLL"), ("EDDF", "LFPG"), ("EDDF", "EHAM"),
    ("EDDF", "EDDM"), ("EDDF", "LIRF"), ("EDDF", "EDDT"), ("LEMF", "EDDF"),
    ("LEBL", "EDDF"), ("EDDM", "LFPG"), ("EDDM", "EHAM"), ("EDDM", "EDDF"),
    ("EDDM", "LIRF"), ("EDDM", "EDDT"), ("LIRF", "EDDF"), ("LIRF", "LICJ"),
    ("EIDW", "EGLL"), ("EIDW", "EDDF"), ("EIDW", "EGPH"), ("ESSA", "EFHK"),
    ("EDDT", "EHAM"), ("EDDT", "EDDF"), ("EDDT", "ESSA"), ("EDDT", "EPWA"),
    ("EFHK", "EDDF"), ("EPWA", "EDDF"), ("EGPH", "EDDF"), ("EGPH", "EIDW"),
    ("LICJ", "EDDF"), ("LICJ", "LIRF")
]




fig, ax = plt.subplots(figsize=(12, 12), subplot_kw={'projection': ccrs.PlateCarree()})


ax.add_feature(cfeature.LAND, color='whitesmoke')
ax.add_feature(cfeature.OCEAN, color='aliceblue')
ax.add_feature(cfeature.COASTLINE)
ax.add_feature(cfeature.BORDERS, linestyle='--', edgecolor='gray')


for start, end in routes:
    if start in airports and end in airports:
        lon1, lat1 = airports[start][::-1]
        lon2, lat2 = airports[end][::-1]
        ax.plot([lon1, lon2], [lat1, lat2], color='blue', linewidth=1, alpha=0.7, transform=ccrs.PlateCarree())

for code, coords in airports.items():
    plt.scatter(coords[1], coords[0], color='red', s=20, transform=ccrs.PlateCarree())
    plt.text(coords[1] + 0.5, coords[0], code, fontsize=10, transform=ccrs.PlateCarree())


plt.show()
