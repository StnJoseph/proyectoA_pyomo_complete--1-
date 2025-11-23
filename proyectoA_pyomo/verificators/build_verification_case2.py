import pandas as pd
from pathlib import Path

# Carpeta raíz del proyecto (la misma lógica que en solve.py)
DATA_DIR = Path(__file__).resolve().parents[1]


def _load_inputs_and_outputs():
    """
    Carga los insumos necesarios:
    - inputs/nodes_clients.csv
    - inputs/nodes_centers.csv
    - inputs/vehicles.csv
    - outputs/tables/selected_arcs_detailed.csv
    - outputs/tables/vehicle_kpis.csv
    """
    inputs_dir = DATA_DIR / "inputs"
    tables_dir = DATA_DIR / "outputs" / "tables"

    nodes_clients = pd.read_csv(inputs_dir / "nodes_clients.csv")
    nodes_centers = pd.read_csv(inputs_dir / "nodes_centers.csv")
    vehicles = pd.read_csv(inputs_dir / "vehicles.csv")

    arcs = pd.read_csv(tables_dir / "selected_arcs_detailed.csv")
    veh_kpis = pd.read_csv(tables_dir / "vehicle_kpis.csv")

    # Normalizar tipos de id a string
    nodes_clients["id"] = nodes_clients["id"].astype(str)
    nodes_centers["id"] = nodes_centers["id"].astype(str)
    vehicles["id"] = vehicles["id"].astype(str)

    arcs["vehicle"] = arcs["vehicle"].astype(str)
    arcs["from"] = arcs["from"].astype(str)
    arcs["to"] = arcs["to"].astype(str)

    veh_kpis["vehicle"] = veh_kpis["vehicle"].astype(str)

    return nodes_clients, nodes_centers, vehicles, arcs, veh_kpis


def _hhmm_from_hours(h):
    """
    Convierte una cantidad de horas (float) a cadena "HH:MM".
    Ej: 8.5 -> "08:30"
    """
    total_minutes = int(round(float(h) * 60))
    hh = (total_minutes // 60) % 24
    mm = total_minutes % 60
    return f"{hh:02d}:{mm:02d}"


def build_verification_case2(start_hour=8.0):
    """
    Construye el archivo verificacion_caso2.csv siguiendo el formato del enunciado.

    Columnas:
    - VehicleId
    - VehicleType
    - InitialLoad
    - RouteSequence
    - ClientsServed
    - DemandSatisfied
    - ArrivalTimes
    - TotalDistance
    - TotalTime
    - Cost
    """
    (
        nodes_clients,
        nodes_centers,
        vehicles,
        arcs,
        veh_kpis,
    ) = _load_inputs_and_outputs()

    client_ids = set(nodes_clients["id"])
    center_ids = set(nodes_centers["id"])

    # Diccionarios auxiliares
    demand_map = nodes_clients.set_index("id")["demand"].to_dict()

    if "type" in vehicles.columns:
        veh_type_map = vehicles.set_index("id")["type"].to_dict()
    elif "VehicleType" in vehicles.columns:
        veh_type_map = vehicles.set_index("id")["VehicleType"].to_dict()
    else:
        # Fallback genérico
        veh_type_map = {row["id"]: "vehicle" for _, row in vehicles.iterrows()}

    veh_kpis_idx = veh_kpis.set_index("vehicle")

    # Para lookup rápido de tiempos por arco (para cada vehículo)
    # Vamos a agrupar por vehículo y construir diccionarios (from, to) -> time_h
    time_maps = {}
    for k, sub in arcs.groupby("vehicle"):
        time_maps[k] = {
            (row["from"], row["to"]): float(row["time_h"])
            for _, row in sub.iterrows()
        }

    rows = []

    # Recorremos vehículos que tienen al menos un arco seleccionado
    for veh_id, veh_arcs in arcs.groupby("vehicle"):
        # Construir sucesores y predecesores para este vehículo
        succ = {}
        pred = {}
        for _, r in veh_arcs.iterrows():
            i = r["from"]
            j = r["to"]
            succ[i] = j
            pred[j] = i

        # Determinar centro de inicio:
        # buscamos un nodo centro que tenga arco saliendo y que no tenga predecesor.
        centers_with_out = [n for n in succ.keys() if n in center_ids]
        start = None
        for c in centers_with_out:
            if c not in pred:
                start = c
                break
        # Si no encontramos, tomamos el primero que sea centro (fallback)
        if start is None and centers_with_out:
            start = centers_with_out[0]

        # Si no hay centro claro, saltamos este vehículo
        if start is None:
            continue

        # Reconstruimos la secuencia de nodos: centro -> ... -> centro
        seq = [start]
        current = start
        visited = {start}

        # límite de seguridad para evitar ciclos infinitos
        for _ in range(len(succ) + 5):
            if current not in succ:
                break
            nxt = succ[current]
            seq.append(nxt)
            if nxt == start:  # cerró el tour
                break
            if nxt in visited:
                # Hay subtour raro; cortamos para no entrar en bucle
                break
            visited.add(nxt)
            current = nxt

        # Clientes en el orden de la secuencia
        clients_seq = [n for n in seq if n in client_ids]
        if not clients_seq:
            # Vehículo sin clientes (probablemente inactivo o solo arco centro-centro)
            continue

        # Demandas atendidas en orden
        demands = [float(demand_map.get(c, 0.0)) for c in clients_seq]
        demand_str = "-".join(
            str(int(d)) if abs(d - int(d)) < 1e-6 else f"{d:.1f}"
            for d in demands
        )

        # ArrivalTimes: acumulamos tiempos desde la hora de inicio
        time_map = time_maps.get(veh_id, {})
        arrival_times = []
        t = float(start_hour)
        current = seq[0]
        for nxt in seq[1:]:
            dt = float(time_map.get((current, nxt), 0.0))
            t += dt
            if nxt in client_ids:
                arrival_times.append(_hhmm_from_hours(t))
            current = nxt
        arrival_str = "-".join(arrival_times)
        
        initial_load = sum(demands)

        # Totales de dist, tiempo, costo, carga
        if veh_id in veh_kpis_idx.index:
            row_kpi = veh_kpis_idx.loc[veh_id]
            total_dist = float(row_kpi["distance_km"])
            total_time = float(row_kpi["time_h"])
            total_cost = float(row_kpi["cost"])
        else:
            # Fallback
            used = veh_arcs
            total_dist = float(used["dist_km"].sum())
            total_time = float(used["time_h"].sum())
            total_cost = float(used["cost"].sum())

        route_str = "-".join(seq)
        depot_id = start                    # centro de inicio
        total_time_min = total_time * 60.0  # minutos

        rows.append(
            {
                "VehicleId": veh_id,
                "DepotId": depot_id,
                "InitialLoad": initial_load,
                "RouteSequence": route_str,
                "ClientsServed": len(clients_seq),
                "DemandsSatisfied": demand_str,
                "TotalDistance": total_dist,
                "TotalTime": total_time_min,
                "FuelCost": total_cost,  # usamos el costo total como FuelCost
            }
        )


    verif_df = pd.DataFrame(rows)

    cols = [
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
    verif_df = verif_df[cols]

    # Guardamos en outputs/verificacion_caso2.csv
    out_path = DATA_DIR / "verificators" / "outputs" / "verificacion_caso2.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    verif_df.to_csv(out_path, index=False)

    print(f"Archivo de verificación generado en: {out_path}")


if __name__ == "__main__":
    build_verification_case2()
