import geopandas as gpd
import pandas as pd
import numpy as np
import folium
import datetime as dt
import matplotlib.pyplot as plt 
import matplotlib
import folium
from folium.plugins import HeatMap
import random

fire = pd.read_csv("Fire_Incidents.csv")
fire.head()

fire = fire[fire["category"] != "false_alarm"]

def rename(string):
    strings = string.split("_")
    string_new = ""
    for i in strings:
        string_new +=  i.capitalize() + " " 
    return string_new

x = fire.groupby("category")
grouped = pd.DataFrame(x.size().reset_index(name = "count"))

for idx, row in grouped.iterrows():
    grouped.loc[idx, "category"] = rename(row["category"])

grouped = grouped.sort_values("count", ascending=False)
print(grouped)


matplotlib.style.use("classic")
ax = grouped.plot(x = "category" , kind="barh", color="#800000", figsize=(10,5), title="Category of fire incidents in Lethbridge, Canada")
ax.yaxis.set_label_text("")
ax.title.set_size(20)
fig = ax.get_figure()
fig.savefig("Category_Fire.png", dpi=500)

# Creating maps
lethbridge = [49.69999, -112.81856]

# HeatMap of fire incidents 
heatmap_lethbridge = folium.Map(location=lethbridge, zoom_start=12.5, tiles="CartoDB dark_matter")
lethbridge_heatmap = HeatMap(fire[["Y", "X"]].dropna(), radius=8, gradient={0.2:"blue", 0.4:"purple", 0.6:"orange", 1.0:"red"}).add_to(map_lethbridge)
heatmap_lethbridge.save("map_lethbridge_HeatMap.html")

# Interactive web map of fire incidents 
pointMap_lethbridge = folium.Map(location=lethbridge, zoom_start=12.5, tiles="CartoDB dark_matter")

for index, row in fire.iterrows():
    
    category = row["category"]
    
    date = str(row['_date']).split("+")[0]

    #hexadecimal = ["#"+''.join([random.choice('ABCDEF0123456789') for i in range(6)])]
    
    if category == "detector_activation":
        _color = "#ff4e50"
    elif category == "small_fire":
        _color = "#fc913a"
    elif category == "fire_pit" :
        _color = "#f9d62e"
    elif category == "motor_vehicle_collision":
        _color = "#eae374"
    else:
        _color = "#e2f4c7"
        
    category = rename(str(row["category"]))
              
    lat, lon = row['Y'], row['X']
        
    _popup = str(category) + ' at ' + str(row['title']) + ' on ' + str(date)+ ' '
    
    folium.CircleMarker(location=[lat, lon], radius = 1, popup=_popup, color=_color, fill=True).add_to(map_lethbridge2)

pointMap_lethbridge.save("map_lethbridge_fire.html")