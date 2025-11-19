# build_verificacion_caso1.py
# Genera verificacion_caso1.csv a partir de la solución del modelo
#
# Requiere:
# - inputs/nodes_clients.csv
# - inputs/nodes_centers.csv
# - inputs/vehicles.csv
# - outputs/tables/selected_arcs_detailed.csv
#
# Salida:
# - verificacion_caso1.csv en la raíz del proyecto

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[0]

INPUTS_DIR = ROOT / "inputs"
TABLES_DIR = ROOT / "outputs" / "tables"
VERIF_PATH = ROOT / "verificacion_caso1.csv"


def build_verificacion():
    # --- Leer datos de entrada ya preprocesados ---
    nodes_clients = pd.read_csv(INPUTS_DIR / "nodes_clients.csv")
    nodes_centers = pd.read_csv(INPUTS_DIR / "nodes_centers.csv")
    vehicles = pd.read_csv(INPUTS_DIR / "vehicles.csv")

    sel = pd.read_csv(TABLES_DIR / "selected_arcs_detailed.csv")

    # Mapas útiles
    demand_map = nodes_clients.set_index("id")["demand"].to_dict()
    center_ids = set(nodes_centers["id"].unique())
    veh_cap = vehicles.set_index("id")["Q"].to_dict()

    # Asegurarnos de que tenemos dist_km, time_h, cost en sel_df
    # (si por alguna razón no están, habría que volver a revisar export_solution)
    for col in ["dist_km", "time_h", "cost"]:
        if col not in sel.columns:
            raise ValueError(f"Falta la columna '{col}' en selected_arcs_detailed.csv")

    rows = []

    # --- Reconstruir una ruta por vehículo ---
    for veh_id in sorted(sel["vehicle"].unique()):
        arcs_v = sel[sel["vehicle"] == veh_id].copy()
        if arcs_v.empty:
            continue  # vehículo no usado

        # Construir mapa i -> j (suponiendo una sola salida por nodo)
        next_map = {}
        for _, r in arcs_v.iterrows():
            i = r["from"]
            j = r["to"]
            next_map[i] = j

        # Determinar el centro (depot) para esta ruta
        depot_candidates = [n for n in next_map.keys() if n in center_ids]
        if depot_candidates:
            depot = depot_candidates[0]
        else:
            # fallback: tomar el primer center global
            depot = nodes_centers["id"].iloc[0]

        # Seguir la ruta desde el depot
        seq = [depot]
        visited = set([depot])
        current = depot

        while True:
            if current not in next_map:
                break
            nxt = next_map[current]
            seq.append(nxt)
            if nxt == depot:
                break
            if nxt in visited:
                # ciclo raro, paramos para no quedar en bucle
                break
            visited.add(nxt)
            current = nxt

        # Clientes en ruta (nodos que no son centros)
        client_ids = [n for n in seq if n in demand_map]

        # Demandas servidas por ese vehículo
        demands = [float(demand_map[c]) for c in client_ids]
        total_demand_served = sum(demands)

        # Distancia / tiempo / costo totales del vehículo
        total_dist = arcs_v["dist_km"].sum()
        total_time = arcs_v["time_h"].sum()
        total_cost = arcs_v["cost"].sum()  # en tu caso base = FuelCost

        # Carga inicial: aquí usamos la capacidad del vehículo
        initial_load = float(veh_cap.get(veh_id, total_demand_served))

        # Construir campos tipo string
        route_seq_str = "-".join(seq) if seq else ""
        clients_served_str = "-".join(client_ids) if client_ids else ""
        demands_str = "-".join(str(int(d)) if d.is_integer() else str(d) for d in demands)

        row = {
            "VehicleId": veh_id,
            "DepotId": depot,
            "InitialLoad": initial_load,
            "RouteSequence": route_seq_str,
            "ClientsServed": clients_served_str,
            "DemandsSatisfied": demands_str,
            "TotalDistance": total_dist,
            "TotalTime": total_time,
            "FuelCost": total_cost,
        }
        rows.append(row)

    verif_df = pd.DataFrame(rows)

    # Ordenar columnas en el orden que pide el README
    cols_order = [
        "VehicleId",
        "DepotId",
        "InitialLoad",
        "RouteSequence",
        "ClientsServed",
        "DemandsSatisfied",
        "TotalDistance",
        "TotalTime",
        "FuelCost",
    ]
    verif_df = verif_df[cols_order]

    verif_df.to_csv(VERIF_PATH, index=False)
    print(f"Archivo generado: {VERIF_PATH}")


if __name__ == "__main__":
    build_verificacion()
