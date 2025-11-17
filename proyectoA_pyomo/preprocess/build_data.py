
# -*- coding: utf-8 -*-
import math
import json
from pathlib import Path
import pandas as pd
import numpy as np

def haversine_km(lat1, lon1, lat2, lon2, R=6371.0):
    phi1 = math.radians(lat1); phi2 = math.radians(lat2)
    dphi = math.radians(lat2-lat1)
    dlambda = math.radians(lon2-lon1)
    a = (math.sin(dphi/2)**2 + 
         math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2)
    return 2*R*math.asin(math.sqrt(a))

def build_data(data_dir:str):
    data_dir = Path(data_dir)
    centers = pd.read_csv(data_dir/"data/raw/nodes_centers.csv")
    clients = pd.read_csv(data_dir/"data/raw/nodes_clients.csv")
    vehicles = pd.read_csv(data_dir/"data/params/vehicles.csv")
    access = pd.read_csv(data_dir/"data/params/access.csv")
    globals_p = json.loads(Path(data_dir/"data/params/global.json").read_text(encoding="utf-8"))
    alpha = float(globals_p.get("alpha_detour", 1.25))
    R = float(globals_p.get("earth_radius_km", 6371.0))

    # Copias espejo para LaTeX
    out_tables = data_dir/"outputs/tables"
    out_tables.mkdir(parents=True, exist_ok=True)
    centers.to_csv(out_tables/"nodes_centers.csv", index=False)
    clients.to_csv(out_tables/"nodes_clients.csv", index=False)

    # Armar N = C ∪ I, con coords y type
    nodes_c = centers[["id","name","lat","lon"]].copy()
    nodes_c["type"]="C"
    nodes_i = clients[["id","name","lat","lon"]].copy()
    nodes_i["type"]="I"
    nodes = pd.concat([nodes_c, nodes_i], ignore_index=True)

    # Diccionarios de coords
    coords = nodes.set_index("id")[["lat","lon"]].to_dict(orient="index")

    # Todas las parejas i != j
    pairs = []
    for i in nodes["id"]:
        for j in nodes["id"]:
            if i==j: 
                continue
            lat1, lon1 = coords[i]["lat"], coords[i]["lon"]
            lat2, lon2 = coords[j]["lat"], coords[j]["lon"]
            dist = haversine_km(lat1, lon1, lat2, lon2, R=R) * alpha
            pairs.append((i,j,dist))
    arcs_df = pd.DataFrame(pairs, columns=["from","to","dist_km"])

    # Expandir por vehículo y computar tiempos/costos
    veh_params = vehicles.set_index("id")

    def row_expand(row):
        out = []
        for k in veh_params.index:
            speed = float(veh_params.loc[k,"speed_kph"])
            eff = float(veh_params.loc[k,"fuel_eff_kmpl"])
            price = float(veh_params.loc[k,"fuel_price_per_l"])
            cost_hour = float(veh_params.loc[k,"cost_hour"])
            time_h = row["dist_km"] / max(1e-6, speed)
            fuel_cost = (row["dist_km"]/max(1e-6, eff)) * price
            time_cost = time_h * cost_hour
            cost = fuel_cost + time_cost
            out.append((k, row["from"], row["to"], row["dist_km"], time_h, cost))
        return out

    expanded = []
    for _, r in arcs_df.iterrows():
        expanded.extend(row_expand(r))
    arcs_cache = pd.DataFrame(expanded, columns=["vehicle","from","to","dist_km","time_h","cost"])

    # Aplicar matriz de acceso: invalidar (from,to) si algún extremo no es permitido para ese vehículo
    # (Esto se filtra en el modelo con x <= A_{i,k} y x <= A_{j,k}; aquí no eliminamos filas, solo dejamos info)
    access_idx = access.set_index(["node","vehicle"])["allowed"].to_dict()
    def allowed_endpoints(v, i, j):
        ai = access_idx.get((i,v), 1)
        aj = access_idx.get((j,v), 1)
        return int(ai and aj)
    arcs_cache["allowed_pair"] = arcs_cache.apply(lambda r: allowed_endpoints(r["vehicle"], r["from"], r["to"]), axis=1)

    # Persistir
    arcs_cache.to_csv(out_tables/"arcs_cache.csv", index=False)

    # Devolver para depuración
    return {
        "centers": centers, "clients": clients, "vehicles": vehicles, 
        "access": access, "arcs_cache": arcs_cache
    }
