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
        "capacity":   depots.get("Capacity", pd.Series([999999])),
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
        "fuel_eff_kmpl":    3.0,
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
    Caso 2 (Proyecto A urbano, multi–depósito).
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

    C_fixed = float(p.get("C_fixed", 0.0))
    C_dist  = float(p.get("C_dist", 0.0))
    C_time  = float(p.get("C_time", 0.0))
    fuel_price = float(p.get("fuel_price", 16300.0))  # COP/galón

    # ---- 2. Nodos clientes (ids estandarizados C001,...) ----
    nodes_clients = pd.DataFrame({
        "id":       clients["StandardizedID"],  # C001,...
        "lat":      clients["Latitude"],
        "lon":      clients["Longitude"],
        "demand":   clients["Demand"],
        "is_center": 0
    })

    # ---- 3. Nodos centros (multi–depósito, con capacidad) ----
    nodes_centers = pd.DataFrame({
        "id":       depots["StandardizedID"],
        "lat":      depots["Latitude"],
        "lon":      depots["Longitude"],
        "capacity": depots["Capacity"],
        "is_center": 1
    })

    # ---- 4. Vehículos internos ----
    # vehicles.csv: VehicleID, VehicleType, StandardizedID, Capacity, Range
    # Eficiencias por tipo se leerán desde parameters_urban.csv si están allí,
    # si no, aplicamos los rangos del README de forma aproximada.

    eff_by_type = {
        "Small Van":  40.0,
        "SmallVan":   40.0,
        "small van":  40.0,
        "Medium Van": 30.0,
        "MediumVan":  30.0,
        "medium van": 30.0,
        "Light Truck": 25.0,
        "LightTruck":  25.0,
        "light truck": 25.0
    }

    # Mapeamos eficiencia al dataframe de vehículos
    def infer_eff(row):
        vtype = str(row["VehicleType"])
        return eff_by_type.get(vtype, 30.0)

    vehicles_internal = vehicles.copy()
    vehicles_internal["fuel_eff_km_per_gal"] = vehicles_internal.apply(infer_eff, axis=1)

    # Creamos la tabla "interna" con las columnas que usa tu modelo
    vehicles_internal = pd.DataFrame({
        "id":             vehicles_internal["StandardizedID"],
        "type":           vehicles_internal["VehicleType"],
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

    # ---- 5. Construir economics.csv (si lo sigues usando) ----
    economics_internal = pd.DataFrame({
        "parameter": ["C_fixed", "C_dist", "C_time", "fuel_price"],
        "value": [C_fixed, C_dist, C_time, fuel_price]
    })

    # ---- 6. Construir arcs_cache ----
    # Hacemos el producto N = centros + clientes
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
                    "allowed_pair": 1
                })

    arcs_df = pd.DataFrame(arcs)

    # ---- 7. Guardar en inputs/ y outputs/tables/ ----
    INPUTS = ROOT / "inputs"
    TABLES = ROOT / "outputs" / "tables"
    INPUTS.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    nodes_centers.to_csv(INPUTS / "nodes_centers.csv", index=False)
    nodes_clients.to_csv(INPUTS / "nodes_clients.csv", index=False)
    vehicles_internal.to_csv(INPUTS / "vehicles.csv", index=False)
    economics_internal.to_csv(INPUTS / "economics.csv", index=False)
    arcs_df.to_csv(INPUTS / "arcs_cache.csv", index=False)

    # espejos opcionales para tablas
    nodes_centers.to_csv(TABLES / "nodes_centers.csv", index=False)
    nodes_clients.to_csv(TABLES / "nodes_clients.csv", index=False)
    arcs_df.to_csv(TABLES / "arcs_cache.csv", index=False)

    print("Preprocessing for Proyecto A – Caso 2 (urbano) completed successfully.")


if __name__=="__main__":
    # Caso 1/ Base
    build_inputs_from_base()
    
    # Caso 2
    # build_inputs_from_caso2()
