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


def build_inputs_from_base():
    """
    Procesa los datos originales de `data/Proyecto_Caso_Base`
    y los convierte al formato interno que tu modelo usa en `inputs/`.
    """
    # MAX_CLIENTS = 30   # <-- prueba con 10 clientes
    # MAX_VEHICLES = None 
    ROOT = str(Path(__file__).resolve().parents[1])

    # ---------------------------
    # 1. Leer datos originales
    # ---------------------------
    base = Path(f"{ROOT}/data/Proyecto_Caso_Base")

    clients = pd.read_csv(base / "clients.csv")
    vehicles = pd.read_csv(base / "vehicles.csv")
    depots   = pd.read_csv(base / "depots.csv")
    params   = pd.read_csv(base / "parameters_base.csv")
    
    pivot = params.set_index("Parameter")["Value"]

    # if MAX_CLIENTS is not None:
    #     # Ordenamos por algún ID estable y tomamos solo los primeros N
    #     clients = clients.sort_values("StandardizedID").head(MAX_CLIENTS).copy()

    # if MAX_VEHICLES is not None:
    #     vehicles = vehicles.sort_values("StandardizedID").head(MAX_VEHICLES).copy()
    
    
    # ---------------------------
    # 2. Construir nodes_clients: id, lat, lon, demand, is_center
    # ---------------------------
    nodes_clients = pd.DataFrame({
        "id":       clients["StandardizedID"],
        "lat":      clients["Latitude"],
        "lon":      clients["Longitude"],
        "demand":   clients["Demand"],
        "is_center": 0
    })

    # ---------------------------
    # 3. Construir nodes_centers
    # ---------------------------
    nodes_centers = pd.DataFrame({
        "id":         depots["StandardizedID"],
        "lat":        depots["Latitude"],
        "lon":        depots["Longitude"],
        "capacity":   depots.get("Capacity", 500),
        "is_center":  1
    })

    # ---------------------------
    # 4. Construir vehicles internos: id, capacity, speed, km_per_l, dep_per_km, hourly_cost
    # ---------------------------

    vehicles_internal = pd.DataFrame({
        "id":               vehicles["StandardizedID"],
        "type":             "base",
        "Q":                vehicles["Capacity"],
        "speed_kph":        40,
        "fuel_eff_kmpl":    30.0,
        "fuel_price_per_l": pivot.get("FuelPrice", 16300),
        "cost_hour":        pivot.get("C_time", 0),
        "fixed_cost":       pivot.get("C_fixed", 0),
        "rango_util_km":    vehicles["Range"],
        "jornada_max_h":    24
    })

    # ---------------------------
    # 5. Construir economics.csv a partir de parameters_base.csv: Parameter, Value, Unit, Description
    # ---------------------------
    pivot = params.set_index("Parameter")["Value"]

    economics_internal = pd.DataFrame({
        "parameter": ["C_fixed", "C_dist", "C_time", "fuel_price"],
        "value": [
            pivot.get("C_fixed", 0),
            pivot.get("C_dist", 0),
            pivot.get("C_time", 0),
            pivot.get("FuelPrice", 16300), # valor sugerido en README base
        ]
    })

    # ---------------------------
    # 6. Construir arcs_cache (centros + clientes)
    # ---------------------------
    N = pd.concat([
        nodes_centers[["id","lat","lon"]],
        nodes_clients[["id","lat","lon"]]
    ], ignore_index=True)

    nodes_dict = {row["id"]:(row["lat"],row["lon"]) for _,row in N.iterrows()}

    arcs = []
    alpha = 1.0
    fuel_price = economics_internal.loc[economics_internal["parameter"]=="fuel_price","value"].values[0]

    for _, v in vehicles_internal.iterrows():
        v_id = v["id"]
        speed = v["speed_kph"]
        kmpl  = v["fuel_eff_kmpl"]

        for i,(lat1,lon1) in nodes_dict.items():
            for j,(lat2,lon2) in nodes_dict.items():
                if i == j:
                    continue
                d = haversine_km(lat1,lon1,lat2,lon2) * alpha
                t = d / max(speed,1e-6)

                fuel_cost = (d / kmpl) * fuel_price
                dist_cost = 0
                time_cost = 0
                total = fuel_cost + dist_cost + time_cost

                arcs.append({
                    "veh": v_id,
                    "i": i,
                    "j": j,
                    "dist_km": round(d,3),
                    "time_h": round(t,3),
                    "cost": round(total,3),
                    "fuel_cost": round(fuel_cost, 3),
                    "dist_cost": 0.0,
                    "time_cost": 0.0, 
                    "allowed_pair": 1
                })

    arcs_df = pd.DataFrame(arcs)

    # ---------------------------
    # 7. Guardar todo en `inputs/` y espejos en `outputs/tables/`
    # ---------------------------
    INPUTS = Path(f"{ROOT}/inputs")
    TABLES = Path(f"{ROOT}/outputs/tables")
    INPUTS.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    # Entradas para el modelo
    nodes_centers.to_csv(INPUTS / "nodes_centers.csv", index=False)
    nodes_clients.to_csv(INPUTS / "nodes_clients.csv", index=False)
    vehicles_internal.to_csv(INPUTS / "vehicles.csv", index=False)
    economics_internal.to_csv(INPUTS / "economics.csv", index=False)
    arcs_df.to_csv(INPUTS / "arcs_cache.csv", index=False)

    # Espejos para tablas / compatibilidad con código original
    nodes_centers.to_csv(TABLES / "nodes_centers.csv", index=False)
    nodes_clients.to_csv(TABLES / "nodes_clients.csv", index=False)
    arcs_df.to_csv(TABLES / "arcs_cache.csv", index=False)

    print("Preprocessing for CVRP Base Case completed successfully.")


def build_inputs_from_caso2():
    """
    Caso 2 (Proyecto A urbano, multi-depósito).
    Lee data/Proyecto_A_Caso2 y construye los inputs/ que usa el modelo.
    """

    ROOT = Path(__file__).resolve().parents[1]
    base = ROOT / "data" / "Proyecto_A_Caso2"

    # ---- 1. Leer datos origen ----
    clients = pd.read_csv(base / "clients.csv")
    vehicles = pd.read_csv(base / "vehicles.csv")
    depots   = pd.read_csv(base / "depots.csv")
    params   = pd.read_csv(base / "parameters_urban.csv")

    # params_urban: Parameter,Value,Unit,Description
    p = params.set_index("Parameter")["Value"]

    C_fixed = float(p.get("C_fixed", 50000.0))
    C_dist  = float(p.get("C_dist", 2500.0))
    C_time  = float(p.get("C_time", 7600.0))
    fuel_price = float(p.get("fuel_price", 16300.0))

    # ---- 2. Nodos clientes ----
    nodes_clients = pd.DataFrame({
        "id":       clients["StandardizedID"],
        "lat":      clients["Latitude"],
        "lon":      clients["Longitude"],
        "demand":   clients["Demand"],
        "is_center": 0
    })

    # ---- 3. Nodos centros ----
    nodes_centers = pd.DataFrame({
        "id":       depots["StandardizedID"],
        "lat":      depots["Latitude"],
        "lon":      depots["Longitude"],
        "capacity": depots["Capacity"],
        "is_center": 1
    })

    # ---- 4. CORRECCIÓN: Detectar si columnas están invertidas ----
    # Si la columna "StandardizedID" contiene texto como "small van", sabemos que está invertida
    sample_std_id = str(vehicles["StandardizedID"].iloc[0]).strip().lower()
    
    if any(word in sample_std_id for word in ["van", "truck", "small", "medium", "light"]):
        # Columnas invertidas: intercambiar
        print("Columnas VehicleType y StandardizedID invertidas. Corrigiendo...")
        vehicles = vehicles.rename(columns={
            "VehicleType": "_temp_type",
            "StandardizedID": "VehicleType"
        })
        vehicles = vehicles.rename(columns={
            "_temp_type": "StandardizedID"
        })

    # Ahora vehicles tiene:
    # StandardizedID = V001, V002, ...
    # VehicleType = small van, medium van, ...

    # ---- 5. Eficiencias por tipo ----
    eff_by_type = {
        "small van":   40.0,  # Promedio del rango 35-45
        "medium van":  30.0,  # Promedio del rango 25-35
        "light truck": 25.0,  # Promedio del rango 22-28
    }

    def infer_eff(vtype: str) -> float:
        key = str(vtype).strip().lower()
        return eff_by_type.get(key, 30.0)

    vehicles["fuel_eff_km_per_gal"] = vehicles["VehicleType"].apply(infer_eff)

    # Crear tabla interna
    vehicles_internal = pd.DataFrame({
        "id":             vehicles["StandardizedID"].astype(str),
        "type":           vehicles["VehicleType"].astype(str),
        "Q":              vehicles["Capacity"],
        "rango_util_km":  vehicles["Range"],
        "fuel_eff_kmgal": vehicles["fuel_eff_km_per_gal"],
        "fuel_price":     fuel_price,
        "C_dist":         C_dist,
        "C_time":         C_time,
        "fixed_cost":     C_fixed,
        "speed_kph":      25.0,
        "jornada_max_h":  8.0
    })

    # ---- 6. economics.csv ----
    economics_internal = pd.DataFrame({
        "parameter": ["C_fixed", "C_dist", "C_time", "fuel_price"],
        "value": [C_fixed, C_dist, C_time, fuel_price]
    })

    # ---- 7. arcs_cache ----
    N = pd.concat([
        nodes_centers[["id", "lat", "lon"]],
        nodes_clients[["id", "lat", "lon"]]
    ], ignore_index=True)

    nodes_dict = {row["id"]: (row["lat"], row["lon"]) for _, row in N.iterrows()}

    arcs = []
    alpha = 1.0

    for _, v in vehicles_internal.iterrows():
        k = v["id"]
        speed = float(v["speed_kph"])
        eff_kmgal = float(v["fuel_eff_kmgal"])

        for i, (lat1, lon1) in nodes_dict.items():
            for j, (lat2, lon2) in nodes_dict.items():
                if i == j:
                    continue
                d = haversine_km(lat1, lon1, lat2, lon2) * alpha
                t = d / max(speed, 1e-6)
                
                fuel_cost = (d / eff_kmgal) * fuel_price
                dist_cost = C_dist * d
                time_cost = C_time * t
                total = fuel_cost + dist_cost + time_cost

                arcs.append({
                    "vehicle": k,
                    "from": i,
                    "to": j,
                    "dist_km": round(d, 3),
                    "time_h": round(t, 3),
                    "cost": round(total, 3),
                    "fuel_cost": round(fuel_cost, 3),
                    "dist_cost": round(dist_cost, 3),
                    "time_cost": round(time_cost, 3),
                    "allowed_pair": 1
                })

    arcs_df = pd.DataFrame(arcs)

    # ---- 8. Guardar ----
    INPUTS = ROOT / "inputs"
    TABLES = ROOT / "outputs" / "tables"
    INPUTS.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    nodes_centers.to_csv(INPUTS / "nodes_centers.csv", index=False)
    nodes_clients.to_csv(INPUTS / "nodes_clients.csv", index=False)
    vehicles_internal.to_csv(INPUTS / "vehicles.csv", index=False)
    economics_internal.to_csv(INPUTS / "economics.csv", index=False)
    arcs_df.to_csv(INPUTS / "arcs_cache.csv", index=False)

    nodes_centers.to_csv(TABLES / "nodes_centers.csv", index=False)
    nodes_clients.to_csv(TABLES / "nodes_clients.csv", index=False)
    arcs_df.to_csv(TABLES / "arcs_cache.csv", index=False)

    print("Preprocessing for Proyecto A — Caso 2 (urbano) completed successfully.")


def build_inputs_from_caso3(max_clients=None):
    """
    Caso 3 (Proyecto A urbano, multi–depósito, escala grande).
    Lee data/Proyecto_A_Caso3 y construye los inputs/ que usa el modelo,
    incluyendo una matriz de acceso basada en VehicleSizeRestriction.
    """

    ROOT = Path(__file__).resolve().parents[1]
    base = ROOT / "data" / "Proyecto_A_Caso3"

    # ---- 1. Leer datos origen ----
    clients = pd.read_csv(base / "clients.csv")
    vehicles = pd.read_csv(base / "vehicles.csv")
    depots   = pd.read_csv(base / "depots.csv")
    params   = pd.read_csv(base / "parameters_urban.csv")

    # Optional: limitar número de clientes para tests de escalabilidad
    if max_clients is not None:
        clients = clients.sort_values("ClientID").head(max_clients)

    # ---- 2. Parámetros económicos ----
    # parameters_urban.csv: Parameter, Value, Unit, Description
    pivot = params.set_index("Parameter")["Value"]
    C_fixed     = float(pivot.get("C_fixed", 0.0))
    C_dist      = float(pivot.get("C_dist", 0.0))
    C_time      = float(pivot.get("C_time", 0.0))
    fuel_price  = float(pivot.get("fuel_price", 0.0))

    # ---- 3. Nodos internos (centros y clientes) ----
    # depots.csv: DepotID,StandardizedID,LocationID,Longitude,Latitude,Capacity
    nodes_centers = pd.DataFrame({
        "id":       depots["StandardizedID"].astype(str),
        "lat":      depots["Latitude"],
        "lon":      depots["Longitude"],
        "capacity": depots["Capacity"],
        "is_center": 1
    })

    # clients.csv: ClientID,StandardizedID,LocationID,Demand,Longitude,Latitude,VehicleSizeRestriction
    nodes_clients = pd.DataFrame({
        "id":       clients["StandardizedID"].astype(str),
        "lat":      clients["Latitude"],
        "lon":      clients["Longitude"],
        "demand":   clients["Demand"],
        "is_center": 0
    })

    # Guardamos también VehicleSizeRestriction para la matriz de acceso
    client_restr = clients.set_index("StandardizedID")["VehicleSizeRestriction"].to_dict()

    # ---- 4. Vehículos internos ----
    # vehicles.csv: VehicleID,StandardizedID,Capacity,Range,VehicleType
    vehicles_internal = vehicles.copy()
    vehicles_internal["id"]   = vehicles_internal["StandardizedID"].astype(str)
    vehicles_internal["type"] = vehicles_internal["VehicleType"].astype(str)

    # Eficiencia de combustible por tipo (si no la extraemos de params)
    eff_by_type = {
        "small van":   40.0,
        "medium van":  30.0,
        "light truck": 25.0,
    }

    # Si en parameters_urban.csv vinieran eficiencias más finas, aquí se podrían mapear.

    def infer_eff(vtype: str) -> float:
        key = str(vtype).strip().lower()
        return eff_by_type.get(key, 30.0)

    vehicles_internal["fuel_eff_km_per_gal"] = vehicles_internal["VehicleType"].apply(infer_eff)

    vehicles_internal = pd.DataFrame({
        "id":             vehicles_internal["id"],
        "VehicleType":    vehicles_internal["VehicleType"],
        "Q":              vehicles_internal["Capacity"],
        "rango_util_km":  vehicles_internal["Range"],
        "fuel_eff_kmgal": vehicles_internal["fuel_eff_km_per_gal"],
        "fuel_price":     fuel_price,
        "C_dist":         C_dist,
        "C_time":         C_time,
        "fixed_cost":     C_fixed,
        "speed_kph":      25.0,
        "jornada_max_h":  8.0
    })

    # ---- 5. economics.csv (si lo usas aún) ----
    economics_internal = pd.DataFrame({
        "parameter": ["C_fixed", "C_dist", "C_time", "fuel_price"],
        "value": [C_fixed, C_dist, C_time, fuel_price]
    })

    # ---- 6. Construir arcs_cache ----
    N = pd.concat([
        nodes_centers[["id", "lat", "lon"]],
        nodes_clients[["id", "lat", "lon"]]
    ], ignore_index=True)

    nodes_dict = {row["id"]: (row["lat"], row["lon"]) for _, row in N.iterrows()}

    arcs = []
    alpha = 1.0  # factor de rodeo urbano (1 = Haversine directo)

    for _, v in vehicles_internal.iterrows():
        k = v["id"]
        speed = float(v["speed_kph"])
        eff_kmgal = float(v["fuel_eff_kmgal"])

        for i, (lat_i, lon_i) in nodes_dict.items():
            for j, (lat_j, lon_j) in nodes_dict.items():
                if i == j:
                    continue

                d = haversine_km(lat_i, lon_i, lat_j, lon_j) * alpha
                t = d / speed if speed > 0 else 0.0

                fuel_gal   = d / eff_kmgal if eff_kmgal > 0 else 0.0
                fuel_cost  = fuel_gal * fuel_price
                dist_cost  = d * C_dist
                time_cost  = t * C_time
                total      = fuel_cost + dist_cost + time_cost

                arcs.append({
                    "vehicle": k,
                    "from": i,
                    "to": j,
                    "dist_km": round(d, 3),
                    "time_h":  round(t, 3),
                    "cost":    round(total, 3),
                    "allowed_pair": 1
                })

    arcs_df = pd.DataFrame(arcs)

    # ---- 7. Matriz de acceso usando VehicleSizeRestriction ----
    # VehicleSizeRestriction: máximo tipo permitido (small van, medium van, light truck)
    type_rank = {
        "small van":   1,
        "medium van":  2,
        "light truck": 3
    }

    def rank_of_type(vtype: str) -> int:
        return type_rank.get(str(vtype).strip().lower(), max(type_rank.values()))

    access_rows = []

    # Centros: permitimos cualquier vehículo
    for _, dep in nodes_centers.iterrows():
        node_id = dep["id"]
        for _, v in vehicles_internal.iterrows():
            access_rows.append({
                "node": node_id,
                "vehicle": v["id"],
                "allowed": 1
            })

    # Clientes: restringimos según VehicleSizeRestriction
    for _, cl in nodes_clients.iterrows():
        node_id = cl["id"]
        restr = client_restr.get(node_id, None)
        if restr is None:
            max_rank = max(type_rank.values())
        else:
            max_rank = rank_of_type(restr)

        for _, v in vehicles_internal.iterrows():
            vtype_rank = rank_of_type(v["VehicleType"])
            allowed = 1 if vtype_rank <= max_rank else 0
            access_rows.append({
                "node": node_id,
                "vehicle": v["id"],
                "allowed": allowed
            })

    access_df = pd.DataFrame(access_rows)

    # ---- 8. Guardar en inputs/ y outputs/tables/ ----
    INPUTS = ROOT / "inputs"
    TABLES = ROOT / "outputs" / "tables"
    INPUTS.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    nodes_centers.to_csv(INPUTS / "nodes_centers.csv", index=False)
    nodes_clients.to_csv(INPUTS / "nodes_clients.csv", index=False)
    vehicles_internal.to_csv(INPUTS / "vehicles.csv", index=False)
    economics_internal.to_csv(INPUTS / "economics.csv", index=False)
    arcs_df.to_csv(INPUTS / "arcs_cache.csv", index=False)
    arcs_df.to_csv(TABLES / "arcs_cache.csv", index=False)
    access_df.to_csv(INPUTS / "access.csv", index=False)

    print("Caso 3 inputs built successfully.")


if __name__=="__main__":
    # Caso 1/ Base
    # build_inputs_from_base()
    
    # Caso 2
    build_inputs_from_caso2()
    
    # Caso 3
    # build_inputs_from_caso3(max_clients=20)
