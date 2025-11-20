# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
from pyomo.environ import (
    ConcreteModel, Set, Param, Var, NonNegativeReals, Binary,
    Objective, Constraint, minimize
)

def _read_first_existing(path_candidates):
    """
    Devuelve el primer CSV existente en la lista de paths.
    Lanza FileNotFoundError si ninguno existe.
    """
    for p in path_candidates:
        if p.exists():
            return pd.read_csv(p)
    raise FileNotFoundError(f"Ninguno de los archivos existe: {path_candidates}")

def build_model(data_dir: str):
    """
    Construye el modelo Pyomo de LogistiCo.

    Diseñado para:
    - Caso Base (Proyecto_Caso_Base) usando inputs/ generados por preprocess.py
    - Proyecto A Caso 2, siempre que preprocess.py también genere inputs/ coherentes.

    Supone que preprocess.py ya escribió:
      inputs/nodes_centers.csv
      inputs/nodes_clients.csv
      inputs/vehicles.csv
      outputs/tables/arcs_cache.csv
    (y opcionalmente algún access.csv / access_matrix.csv)
    """
    root = Path(data_dir)

    # ---------------------------
    # 1. Leer datos
    # ---------------------------
    centers = _read_first_existing([
        root / "inputs" / "nodes_centers.csv",
        root / "data" / "raw" / "nodes_centers.csv",
    ])

    clients = _read_first_existing([
        root / "inputs" / "nodes_clients.csv",
        root / "data" / "raw" / "nodes_clients.csv",
    ])

    vehicles = _read_first_existing([
        root / "inputs" / "vehicles.csv",
        root / "data" / "params" / "vehicles.csv",
    ])

    # arcs_cache: preferimos el espejo en outputs/tables (coherente con solve.py)
    arcs_cache = _read_first_existing([
        root / "outputs" / "tables" / "arcs_cache.csv",
        root / "inputs" / "arcs_cache.csv",
    ])

    # access es opcional (para Caso Base no existe)
    access = None
    for p in [
        root / "data" / "params" / "access.csv",
        root / "data" / "params" / "access_matrix.csv",
        root / "inputs" / "access.csv",
    ]:
        if p.exists():
            access = pd.read_csv(p)
            break

    # Normalizar tipos de id a string
    centers["id"] = centers["id"].astype(str)
    clients["id"] = clients["id"].astype(str)
    vehicles["id"] = vehicles["id"].astype(str)

    # ---------------------------
    # 2. Normalizar columnas clave
    # ---------------------------
    # demanda: q o demand
    if "q" in clients.columns:
        demand_col = "q"
    elif "demand" in clients.columns:
        demand_col = "demand"
    else:
        raise KeyError(
            "nodes_clients.csv debe tener una columna 'q' o 'demand' para la demanda."
        )

    # capacidad de centro: cap o capacity
    if "cap" in centers.columns:
        cap_col = "cap"
    elif "capacity" in centers.columns:
        cap_col = "capacity"
    else:
        # en Caso Base podría no ser tan relevante, pero mejor exigir algo
        raise KeyError(
            "nodes_centers.csv debe tener una columna 'cap' o 'capacity' para la capacidad del CD."
        )

    # vehículos: aseguramos las columnas que usa el modelo
    vehicles = vehicles.set_index("id").copy()

    # Q (capacidad de vehículo)
    if "Q" not in vehicles.columns:
        if "capacity" in vehicles.columns:
            vehicles["Q"] = vehicles["capacity"]
        elif "Capacity" in vehicles.columns:
            vehicles["Q"] = vehicles["Capacity"]
        else:
            raise KeyError("vehicles.csv debe tener 'Q' o alguna columna de capacidad ('capacity').")

    # fixed_cost, rango, jornada: si no existen, dar valores seguros
    if "fixed_cost" not in vehicles.columns:
        vehicles["fixed_cost"] = 0.0
    if "rango_util_km" not in vehicles.columns:
        vehicles["rango_util_km"] = 1e6  # rango prácticamente ilimitado si no se especifica
    if "jornada_max_h" not in vehicles.columns:
        vehicles["jornada_max_h"] = 1e6  # jornada muy grande si no se especifica

    # ---------------------------
    # 3. Normalizar arcs_cache ('veh','i','j' -> 'vehicle','from','to')
    # ---------------------------
    if "veh" in arcs_cache.columns and "vehicle" not in arcs_cache.columns:
        arcs_cache = arcs_cache.rename(columns={
            "veh": "vehicle",
            "i": "from",
            "j": "to"
        })

    # Asegurar columnas básicas
    required_arc_cols = {"vehicle", "from", "to", "dist_km", "time_h", "cost"}
    missing = required_arc_cols - set(arcs_cache.columns)
    if missing:
        raise KeyError(
            f"arcs_cache.csv debe contener columnas {required_arc_cols}, faltan: {missing}"
        )

    arcs_cache["vehicle"] = arcs_cache["vehicle"].astype(str)
    arcs_cache["from"] = arcs_cache["from"].astype(str)
    arcs_cache["to"] = arcs_cache["to"].astype(str)

    # ---------------------------
    # 4. Construir modelo Pyomo
    # ---------------------------
    m = ConcreteModel(name="LogistiCo_CVRP")

    # Conjuntos
    m.C = Set(initialize=centers["id"].tolist(), ordered=False)
    m.I = Set(initialize=clients["id"].tolist(), ordered=False)
    m.N = Set(initialize=list(centers["id"]) + list(clients["id"]), ordered=False)
    m.K = Set(initialize=vehicles.index.tolist(), ordered=False)

    # Todos los arcos i != j sobre N
    A_list = [(i, j) for i in m.N.value for j in m.N.value if i != j]
    m.A = Set(dimen=2, initialize=A_list, ordered=False)

    # ---------------------------
    # 5. Parámetros
    # ---------------------------
    # Demanda y capacidad de centros
    q_map = clients.set_index("id")[demand_col].to_dict()
    cap_c_map = centers.set_index("id")[cap_col].to_dict()
    m.q = Param(m.I, initialize=q_map, within=NonNegativeReals, default=0.0)
    m.cap_c = Param(m.C, initialize=cap_c_map, within=NonNegativeReals, default=0.0)

    # Parámetros de vehículos
    Q_map = vehicles["Q"].to_dict()
    f_map = vehicles["fixed_cost"].to_dict()
    rango_map = vehicles["rango_util_km"].to_dict()
    jornada_map = vehicles["jornada_max_h"].to_dict()
    m.Q = Param(m.K, initialize=Q_map, within=NonNegativeReals, default=0.0)
    m.f = Param(m.K, initialize=f_map, within=NonNegativeReals, default=0.0)
    m.rango = Param(m.K, initialize=rango_map, within=NonNegativeReals, default=0.0)
    m.jornada = Param(m.K, initialize=jornada_map, within=NonNegativeReals, default=0.0)

    # Acceso urbano A_{i,k} (si no hay archivo, todo permitido = 1)
    access_idx = {}
    if access is not None and {"node", "vehicle", "allowed"} <= set(access.columns):
        access["node"] = access["node"].astype(str)
        access["vehicle"] = access["vehicle"].astype(str)
        access_idx = access.set_index(["node", "vehicle"])["allowed"].to_dict()

    def A_init(m_, i, k):
        # Si no hay info de acceso, o no hay par específico, por defecto 1
        return float(access_idx.get((i, k), 1.0))

    m.A_access = Param(m.N, m.K, initialize=A_init,
                       within=NonNegativeReals, default=1.0)

    # Costos/tiempos/distancias por (k,i,j) desde arcs_cache
    arcs_cache["key"] = list(zip(
        arcs_cache["vehicle"], arcs_cache["from"], arcs_cache["to"]
    ))
    cost_map = dict(zip(arcs_cache["key"], arcs_cache["cost"]))
    time_map = dict(zip(arcs_cache["key"], arcs_cache["time_h"]))
    dist_map = dict(zip(arcs_cache["key"], arcs_cache["dist_km"]))

    def cost_init(m_, k, i, j):
        return float(cost_map.get((k, i, j), 1e9))

    def time_init(m_, k, i, j):
        return float(time_map.get((k, i, j), 1e6))

    def dist_init(m_, k, i, j):
        return float(dist_map.get((k, i, j), 1e6))

    m.cost = Param(m.K, m.A, initialize=cost_init, within=NonNegativeReals)
    m.time = Param(m.K, m.A, initialize=time_init, within=NonNegativeReals)
    m.dist = Param(m.K, m.A, initialize=dist_init, within=NonNegativeReals)

    # ---------------------------
    # 6. Variables
    # ---------------------------
    m.x = Var(m.K, m.A, domain=Binary)
    m.y = Var(m.K, m.A, domain=NonNegativeReals)
    m.z = Var(m.C, m.K, domain=Binary)
    m.s = Var(m.C, domain=NonNegativeReals)
    m.u = Var(m.K, domain=Binary)

    # ---------------------------
    # 7. Función objetivo
    # ---------------------------
    def obj_rule(m_):
        return sum(m_.cost[k, i, j] * m_.x[k, (i, j)]
                   for k in m_.K for (i, j) in m_.A) + \
               sum(m_.f[k] * m_.u[k] for k in m_.K)

    m.OBJ = Objective(rule=obj_rule, sense=minimize)

    # ---------------------------
    # 8. Restricciones
    # ---------------------------

    # Visita única por cliente
    def visit_in_rule(m_, i):
        return sum(m_.x[k, (j, i)] for k in m_.K for (j, ii) in m_.A if ii == i) == 1

    def visit_out_rule(m_, i):
        return sum(m_.x[k, (i, j)] for k in m_.K for (ii, j) in m_.A if ii == i) == 1

    m.VisitIn = Constraint(m.I, rule=visit_in_rule)
    m.VisitOut = Constraint(m.I, rule=visit_out_rule)

    # Continuidad por vehículo en cada cliente
    def cont_rule(m_, k, i):
        return (
            sum(m_.x[k, (i, j)] for (ii, j) in m_.A if ii == i) -
            sum(m_.x[k, (j, i)] for (j, ii) in m_.A if ii == i)
        ) == 0

    m.Continuity = Constraint(m.K, m.I, rule=cont_rule)

    # Salida/regreso al mismo CD por vehículo
    def start_center_rule(m_, k, c):
        return sum(m_.x[k, (c, j)] for (cc, j) in m_.A if cc == c) == m_.z[c, k]

    def end_center_rule(m_, k, c):
        return sum(m_.x[k, (i, c)] for (i, cc) in m_.A if cc == c) == m_.z[c, k]

    m.StartAtCenter = Constraint(m.K, m.C, rule=start_center_rule)
    m.EndAtCenter = Constraint(m.K, m.C, rule=end_center_rule)

    # Cada vehículo a lo sumo un CD; u_k = sum_c z_{ck}
    def one_center_rule(m_, k):
        return sum(m_.z[c, k] for c in m_.C) == m_.u[k]

    m.AssignOneCenter = Constraint(m.K, rule=one_center_rule)

    # Capacidad por arco (y <= Q * x)
    def cap_arc_rule(m_, k, i, j):
        return m_.y[k, (i, j)] <= m_.Q[k] * m_.x[k, (i, j)]

    m.CapArc = Constraint(m.K, m.A, rule=cap_arc_rule)

    # Conservación de flujo en clientes (agregado sobre k)
    def cons_client_rule(m_, i):
        return (
            sum(m_.y[k, (j, i)] for k in m_.K for (j, ii) in m_.A if ii == i) -
            sum(m_.y[k, (i, j)] for k in m_.K for (ii, j) in m_.A if ii == i)
        ) == m_.q[i]

    m.FlowClients = Constraint(m.I, rule=cons_client_rule)

    # Balance en centros y capacidad de centro
    def cons_center_rule(m_, c):
        return (
            sum(m_.y[k, (c, j)] for k in m_.K for (cc, j) in m_.A if cc == c) -
            sum(m_.y[k, (j, c)] for k in m_.K for (j, cc) in m_.A if cc == c)
        ) == m_.s[c]

    m.FlowCenters = Constraint(m.C, rule=cons_center_rule)

    def cap_center_rule(m_, c):
        return m_.s[c] <= m_.cap_c[c]

    m.CenterCap = Constraint(m.C, rule=cap_center_rule)

    # Acceso urbano (extremos del arco deben ser permitidos)
    def access_i_rule(m_, k, i, j):
        return m_.x[k, (i, j)] <= m_.A_access[i, k]

    def access_j_rule(m_, k, i, j):
        return m_.x[k, (i, j)] <= m_.A_access[j, k]

    m.AccessI = Constraint(m.K, m.A, rule=access_i_rule)
    m.AccessJ = Constraint(m.K, m.A, rule=access_j_rule)

    # Rango útil (km) por vehículo
    def range_rule(m_, k):
        return sum(m_.dist[k, (i, j)] * m_.x[k, (i, j)] for (i, j) in m_.A) <= \
               m_.rango[k] * m_.u[k]

    m.Range = Constraint(m.K, rule=range_rule)

    # Jornada máxima (horas) por vehículo
    def jornada_rule(m_, k):
        return sum(m_.time[k, (i, j)] * m_.x[k, (i, j)] for (i, j) in m_.A) <= \
               m_.jornada[k] * m_.u[k]

    m.Jornada = Constraint(m.K, rule=jornada_rule)

    # Suficiencia de oferta total
    def supply_cover_rule(m_):
        return sum(m_.s[c] for c in m_.C) == sum(m_.q[i] for i in m_.I)

    m.SupplyCover = Constraint(rule=supply_cover_rule)

    return m
