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


def build_inputs_from_cvrp_base():
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
    # 2. Construir nodes_clients (formato interno)
    # ---------------------------
    # Tu formato interno requiere: id, lat, lon, demand, is_center
    nodes_clients = pd.DataFrame({
        "id":       clients["StandardizedID"],      # C001, C002,...
        "lat":      clients["Latitude"],
        "lon":      clients["Longitude"],
        "demand":   clients["Demand"],
        "is_center": 0
    })

    # ---------------------------
    # 3. Construir nodes_centers
    # ---------------------------
    nodes_centers = pd.DataFrame({
        "id":         depots["StandardizedID"],      # CD01
        "lat":        depots["Latitude"],
        "lon":        depots["Longitude"],
        # Si tu modelo no usa capacidad de depot en caso base, pon un valor grande.
        "capacity":   depots.get("Capacity", pd.Series([999999])),
        "is_center":  1
    })

    # ---------------------------
    # 4. Construir vehicles internos
    # ---------------------------
    # Tu archivo interno de vehicles solía tener columnas como: id, capacity, speed, km_per_l, dep_per_km, hourly_cost
    # Para el Caso Base solo tenemos Capacity y Range, así que:
    # Pondremos columnas mínimas necesarias y valores por defecto para que no explote el modelo.

    vehicles_internal = pd.DataFrame({
        "id":               vehicles["StandardizedID"],      # V001, V002, ...
        "type":             "base",                          # etiqueta genérica
        "Q":                vehicles["Capacity"],            # capacidad de carga
        "speed_kph":        40,                              # asumimos 40 km/h
        "fuel_eff_kmpl":    3.0,                             # p.ej. 3 km/L
        "fuel_price_per_l": pivot.get("FuelPrice", 16300),   # COP/L
        "cost_hour":        pivot.get("C_time", 0),          # C_time del caso base
        "fixed_cost":       pivot.get("C_fixed", 0),         # C_fixed del caso base
        "rango_util_km":    vehicles["Range"],               # autonomía
        "jornada_max_h":    24                              # jornada grande (no activa realmente)
    })

    # ---------------------------
    # 5. Construir economics.csv a partir de parameters_base.csv
    # ---------------------------
    # parameters_base.csv tiene columnas: Parameter, Value, Unit, Description
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
    # 6. Construir arcs_cache (tu estilo original)
    # ---------------------------
    # Unión de centros + clientes
    N = pd.concat([
        nodes_centers[["id","lat","lon"]],
        nodes_clients[["id","lat","lon"]]
    ], ignore_index=True)

    nodes_dict = {row["id"]:(row["lat"],row["lon"]) for _,row in N.iterrows()}

    arcs = []
    alpha = 1.0  # en Caso Base no se usa desvío; puedes cambiarlo si quieres
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
    # 7. Guardar todo en `inputs/`
    # ---------------------------
    # 7. Guardar todo en `inputs/` y espejos en `outputs/tables/`
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

# ----------------------------------------------------------
#  EJECUCIÓN DIRECTA (en tu estilo original)
# ----------------------------------------------------------
if __name__=="__main__":
    build_inputs_from_cvrp_base()
