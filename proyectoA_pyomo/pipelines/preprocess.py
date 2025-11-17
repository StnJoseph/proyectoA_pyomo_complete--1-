
import os, json, math, pandas as pd
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2-lat1)
    dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

if __name__=="__main__":
    ROOT = str(Path(__file__).resolve().parents[1])
    centers = pd.read_csv(f"{ROOT}/data/raw/nodes_centers.csv")
    clients = pd.read_csv(f"{ROOT}/data/raw/nodes_clients.csv")
    vehicles = pd.read_csv(f"{ROOT}/data/params/vehicles.csv")
    access = pd.read_csv(f"{ROOT}/data/params/access_matrix.csv")
    with open(f"{ROOT}/data/params/global.json","r") as f:
        g = json.load(f)
    alpha = float(g.get("detour_alpha",1.25))
    fuel_price = float(g.get("fuel_price_per_liter",12.0))

    N = pd.concat([centers[["id","lat","lon"]], clients[["id","lat","lon"]]])
    nodes = {row["id"]:(row["lat"],row["lon"]) for _,row in N.iterrows()}

    arcs = []
    for i,(lat1,lon1) in nodes.items():
        for j,(lat2,lon2) in nodes.items():
            if i==j: continue
            d = haversine_km(lat1,lon1,lat2,lon2) * alpha
            for _, v in vehicles.iterrows():
                t = d / max(v["speed_kmph"],1e-6)
                fuel_cost = (d / v["km_per_l"]) * fuel_price
                dist_cost = v["dep_per_km"] * d
                time_cost = v["hourly_cost"] * t
                total = fuel_cost + dist_cost + time_cost
                arcs.append({"veh":v["id"],"i":i,"j":j,"distance_km":round(d,3),"time_h":round(t,3),"cost":round(total,3)})
    arcs_df = pd.DataFrame(arcs)
    # cache for model
    os.makedirs(f"{ROOT}/outputs/tables", exist_ok=True)
    arcs_df.to_csv(f"{ROOT}/outputs/tables/arcs_cache.csv", index=False)

    # mirror nodes to outputs (for LaTeX tables)
    centers.to_csv(f"{ROOT}/outputs/tables/nodes_centers.csv", index=False)
    clients.to_csv(f"{ROOT}/outputs/tables/nodes_clients.csv", index=False)

    print("Preprocess OK.")
