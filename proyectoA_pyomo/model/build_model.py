# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
from pyomo.environ import (
    ConcreteModel, Set, Param, Var, NonNegativeReals, Binary,
    Objective, Constraint, minimize
)

def build_model(root_dir: str):
    """
    Construye el modelo Pyomo usando los archivos generados por el
    preprocesamiento del Caso Base.

    Espera encontrar:
      - inputs/nodes_centers.csv   (id, lat, lon, capacity, is_center)
      - inputs/nodes_clients.csv   (id, lat, lon, demand, is_center)
      - inputs/vehicles.csv        (id, type, Q, speed_kph, fuel_eff_kmpl,
                                    fuel_price_per_l, cost_hour,
                                    fixed_cost, rango_util_km, jornada_max_h)
      - outputs/tables/arcs_cache.csv (veh, i, j, dist_km, time_h, cost, allowed_pair)
    """

    root = Path(root_dir)

    # ------------------------------------------------------------------
    # 1. Leer datos procesados
    # ------------------------------------------------------------------
    centers = pd.read_csv(root / "inputs/nodes_centers.csv")
    clients = pd.read_csv(root / "inputs/nodes_clients.csv")
    vehicles = pd.read_csv(root / "inputs/vehicles.csv")
    arcs_cache = pd.read_csv(root / "outputs/tables/arcs_cache.csv")

    m = ConcreteModel(name="ProyectoA_Urbano_BaseCase")

    # ------------------------------------------------------------------
    # 2. Conjuntos
    # ------------------------------------------------------------------
    m.C = Set(initialize=centers["id"].tolist(), ordered=False)              # centros
    m.I = Set(initialize=clients["id"].tolist(), ordered=False)              # clientes
    m.N = Set(initialize=list(centers["id"]) + list(clients["id"]), ordered=False)
    m.K = Set(initialize=vehicles["id"].tolist(), ordered=False)             # vehículos

    # Todos los arcos (i,j) con i != j
    A_list = [(i, j) for i in m.N for j in m.N if i != j]
    m.A = Set(dimen=2, initialize=A_list, ordered=False)

    # ------------------------------------------------------------------
    # 3. Parámetros de demanda y capacidad de centros
    # ------------------------------------------------------------------
    q_map = clients.set_index("id")["demand"].to_dict()      # demanda por cliente
    cap_c_map = centers.set_index("id")["capacity"].to_dict()  # capacidad por CD

    m.q = Param(m.I, initialize=q_map, within=NonNegativeReals, default=0.0)
    m.cap_c = Param(m.C, initialize=cap_c_map, within=NonNegativeReals, default=0.0)

    # ------------------------------------------------------------------
    # 4. Parámetros de vehículos
    # ------------------------------------------------------------------
    vehicles_idx = vehicles.set_index("id")

    Q_map        = vehicles_idx["Q"].to_dict()
    f_map        = vehicles_idx["fixed_cost"].to_dict()
    rango_map    = vehicles_idx["rango_util_km"].to_dict()
    jornada_map  = vehicles_idx["jornada_max_h"].to_dict()

    m.Q      = Param(m.K, initialize=Q_map,     within=NonNegativeReals, default=0.0)
    m.f      = Param(m.K, initialize=f_map,     within=NonNegativeReals, default=0.0)
    m.rango  = Param(m.K, initialize=rango_map, within=NonNegativeReals, default=0.0)
    m.jornada= Param(m.K, initialize=jornada_map, within=NonNegativeReals, default=0.0)

    # ------------------------------------------------------------------
    # 5. Acceso urbano A_{i,k}
    #    En el Caso Base no hay restricciones de acceso:
    #    todos los vehículos pueden visitar todos los nodos.
    # ------------------------------------------------------------------
    def A_init(m, i, k):
        return 1.0
    m.A_access = Param(m.N, m.K, initialize=A_init,
                       within=NonNegativeReals, default=1.0)

    # ------------------------------------------------------------------
    # 6. Costos, tiempos y distancias por (k,i,j) usando arcs_cache
    # ------------------------------------------------------------------
    # arcs_cache: veh, i, j, dist_km, time_h, cost, allowed_pair
    arcs_cache["key"] = list(zip(arcs_cache["veh"],
                                 arcs_cache["i"],
                                 arcs_cache["j"]))

    cost_map = dict(zip(arcs_cache["key"], arcs_cache["cost"]))
    time_map = dict(zip(arcs_cache["key"], arcs_cache["time_h"]))
    dist_map = dict(zip(arcs_cache["key"], arcs_cache["dist_km"]))

    def cost_init(m, k, i, j):
        return float(cost_map.get((k, i, j), 1e9))

    def time_init(m, k, i, j):
        return float(time_map.get((k, i, j), 1e6))

    def dist_init(m, k, i, j):
        return float(dist_map.get((k, i, j), 1e6))

    m.cost = Param(m.K, m.A, initialize=cost_init, within=NonNegativeReals)
    m.time = Param(m.K, m.A, initialize=time_init, within=NonNegativeReals)
    m.dist = Param(m.K, m.A, initialize=dist_init, within=NonNegativeReals)

    # ------------------------------------------------------------------
    # 7. Variables
    # ------------------------------------------------------------------
    m.x = Var(m.K, m.A, domain=Binary)                # 1 si arco (i,j) usado por k
    m.y = Var(m.K, m.A, domain=NonNegativeReals)      # flujo por arco
    m.z = Var(m.C, m.K, domain=Binary)                # 1 si k asignado a c
    m.s = Var(m.C, domain=NonNegativeReals)           # suministro total desde c
    m.u = Var(m.K, domain=Binary)                     # 1 si vehículo k se activa

    # ------------------------------------------------------------------
    # 8. Función objetivo
    # ------------------------------------------------------------------
    def obj_rule(m):
        return sum(m.cost[k, i, j] * m.x[k, i, j] for k in m.K for (i, j) in m.A) + \
               sum(m.f[k] * m.u[k] for k in m.K)

    m.OBJ = Objective(rule=obj_rule, sense=minimize)

    # ------------------------------------------------------------------
    # 9. Restricciones
    # ------------------------------------------------------------------

    # Visita única por cliente (una entrada y una salida totales entre todos los k)
    def visit_in_rule(m, i):
        return sum(m.x[k, j, i] for k in m.K for (j, ii) in m.A if ii == i) == 1

    def visit_out_rule(m, i):
        return sum(m.x[k, i, j] for k in m.K for (ii, j) in m.A if ii == i) == 1

    m.VisitIn = Constraint(m.I, rule=visit_in_rule)
    m.VisitOut = Constraint(m.I, rule=visit_out_rule)

    # Continuidad por vehículo en cada cliente
    def cont_rule(m, k, i):
        return (sum(m.x[k, i, j] for (ii, j) in m.A if ii == i) -
                sum(m.x[k, j, i] for (j, ii) in m.A if ii == i) == 0)

    m.Continuity = Constraint(m.K, m.I, rule=cont_rule)

    # Salida/regreso al mismo CD por vehículo
    def start_center_rule(m, k, c):
        return sum(m.x[k, c, j] for (cc, j) in m.A if cc == c) == m.z[c, k]

    def end_center_rule(m, k, c):
        return sum(m.x[k, i, c] for (i, cc) in m.A if cc == c) == m.z[c, k]

    m.StartAtCenter = Constraint(m.K, m.C, rule=start_center_rule)
    m.EndAtCenter   = Constraint(m.K, m.C, rule=end_center_rule)

    # Cada vehículo a lo sumo un CD; u_k = sum_c z_{ck}
    def one_center_rule(m, k):
        return sum(m.z[c, k] for c in m.C) == m.u[k]

    m.AssignOneCenter = Constraint(m.K, rule=one_center_rule)

    # Capacidad por arco (y <= Q * x)
    def cap_arc_rule(m, k, i, j):
        return m.y[k, i, j] <= m.Q[k] * m.x[k, i, j]

    m.CapArc = Constraint(m.K, m.A, rule=cap_arc_rule)

    # Conservación de flujo en clientes (agregado sobre k)
    def cons_client_rule(m, i):
        return (sum(m.y[k, j, i] for k in m.K for (j, ii) in m.A if ii == i) -
                sum(m.y[k, i, j] for k in m.K for (ii, j) in m.A if ii == i)
                == m.q[i])

    m.FlowClients = Constraint(m.I, rule=cons_client_rule)

    # Balance en centros y capacidad de centro
    def cons_center_rule(m, c):
        return (sum(m.y[k, c, j] for k in m.K for (cc, j) in m.A if cc == c) -
                sum(m.y[k, j, c] for k in m.K for (j, cc) in m.A if cc == c)
                == m.s[c])

    m.FlowCenters = Constraint(m.C, rule=cons_center_rule)

    def cap_center_rule(m, c):
        return m.s[c] <= m.cap_c[c]

    m.CenterCap = Constraint(m.C, rule=cap_center_rule)

    # Acceso urbano (en Caso Base siempre vale 1)
    def access_i_rule(m, k, i, j):
        return m.x[k, i, j] <= m.A_access[i, k]

    def access_j_rule(m, k, i, j):
        return m.x[k, i, j] <= m.A_access[j, k]

    m.AccessI = Constraint(m.K, m.A, rule=access_i_rule)
    m.AccessJ = Constraint(m.K, m.A, rule=access_j_rule)

    # Rango útil (km) por vehículo
    def range_rule(m, k):
        return sum(m.dist[k, i, j] * m.x[k, i, j] for (i, j) in m.A) <= m.rango[k] * m.u[k]

    m.Range = Constraint(m.K, rule=range_rule)

    # Jornada máxima (horas) por vehículo
    def jornada_rule(m, k):
        return sum(m.time[k, i, j] * m.x[k, i, j] for (i, j) in m.A) <= m.jornada[k] * m.u[k]

    m.Jornada = Constraint(m.K, rule=jornada_rule)

    # Suficiencia de oferta total
    def supply_cover_rule(m):
        return sum(m.s[c] for c in m.C) == sum(m.q[i] for i in m.I)

    m.SupplyCover = Constraint(rule=supply_cover_rule)

    return m
