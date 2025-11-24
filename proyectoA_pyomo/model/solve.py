
import os, json, pandas as pd, numpy as np
from pyomo.opt import SolverStatus, TerminationCondition
from pathlib import Path


DATA_DIR = str(Path(__file__).resolve().parents[1])

def export_arcs_cache():
    # Ensure arcs_cache.csv exists for the MILP (built by preprocess)
    arcs_cache = pd.read_csv(f"{DATA_DIR}/outputs/tables/arcs_cache.csv")
    return arcs_cache

def try_milp():
    try:
        from pyomo.environ import SolverFactory
        from model.build_model import build_model

        m = build_model(DATA_DIR)

        solver = None
        solver_name = None

        # Prioridad: HiGHS > CBC > GLPK
        for s in ["highs", "cbc", "glpk"]:
            if SolverFactory(s).available(exception_flag=False):
                solver = SolverFactory(s)
                solver_name = s
                break

        if solver is None:
            return None, "No solver available"

        TIME_LIMIT = 1200  # <----------------------------- TIME LIMIT EN SEGUNDOS

        if solver_name == "highs":
            solver.options["time_limit"] = TIME_LIMIT
        elif solver_name == "cbc":
            solver.options["seconds"] = TIME_LIMIT
        elif solver_name == "glpk":
            solver.options["tmlim"] = TIME_LIMIT

        print(f"Usando solver: {solver_name} con límite de {TIME_LIMIT} s\n")

        res = solver.solve(m, tee=True)

        status    = res.solver.status
        term_cond = res.solver.termination_condition

        print("Solver status:", status)
        print("Termination condition:", term_cond)

        # 1. Solución óptima o factible
        if term_cond in (TerminationCondition.optimal,
                        TerminationCondition.feasible):
            print("→ Usando solución (optimal/feasible).")
            return m, "OK"

        # 2. Time limit pero con solución factible encontrada
        if term_cond == TerminationCondition.maxTimeLimit and \
        status in (SolverStatus.ok, SolverStatus.aborted):
            print("→ Time limit reached PERO con incumbente factible. Usando mejor solución encontrada.")
            return m, "TIME_LIMIT_FEASIBLE"

        # 3. De lo contrario, fallo real
        return None, f"Solver status: {status}, termination: {term_cond}"

    except Exception as e:
        return None, f"MILP error: {e}"



def export_solution(m):
    # Read input frames
    centers = pd.read_csv(f"{DATA_DIR}/inputs/nodes_centers.csv")
    clients = pd.read_csv(f"{DATA_DIR}/inputs/nodes_clients.csv")
    vehicles = pd.read_csv(f"{DATA_DIR}/inputs/vehicles.csv")
    # Export x arcs
    sel = []
    for k in m.K:
        for (i,j) in m.A:
            if m.x[k,i,j].value and m.x[k,i,j].value > 0.5:
                sel.append({"vehicle":k, "from":i, "to":j})
    sel_df = pd.DataFrame(sel)
    # fetch cost/time/dist from cache
    arcs_df = pd.read_csv(f"{DATA_DIR}/outputs/tables/arcs_cache.csv")
  
    arcs_df = arcs_df.rename(columns={
        "veh": "vehicle",
        "i": "from",
        "j": "to"
    })
    
    sel_df = sel_df.merge(
        arcs_df, 
        on=["vehicle","from","to"], 
        how="left"
    )
    
    sel_df.to_csv(f"{DATA_DIR}/outputs/tables/selected_arcs_detailed.csv", index=False)

    # Export flows
    flows = []
    for k in m.K:
        for (i,j) in m.A:
            v = float(m.y[k,i,j].value) if m.y[k,i,j].value is not None else 0.0
            if v>1e-6:
                flows.append({"vehicle":k,"from":i,"to":j,"flow":v})
    
    flows_df = pd.DataFrame(flows)
    flows_df.to_csv(f"{DATA_DIR}/outputs/tables/flows_by_arc_per_vehicle.csv", index=False)

    # KPIs centers
    center_kpis = []
    for c in m.C:
        s = float(m.s[c].value) if m.s[c].value is not None else 0.0
        cap = float(centers.set_index("id").loc[c,"capacity"])
        center_kpis.append({
            "center":c,
            "supply":s,
            "cap":cap,
            "utilization": s/cap if cap>0 else 0
        })
    pd.DataFrame(center_kpis).to_csv(f"{DATA_DIR}/outputs/tables/center_kpis.csv", index=False)

    # KPIs vehicles
    veh_kpis = []
    for k in m.K:
        used_arcs = sel_df[sel_df["vehicle"] == k]
        dist = used_arcs["dist_km"].sum()
        time = used_arcs["time_h"].sum()
        cost = used_arcs["cost"].sum()

        # carga entregada (flujo que llega a clientes)
        load = 0.0
        for i in m.I:  # Para cada cliente
            # Flujo neto = entra - sale
            flow_in = sum(
                float(m.y[k, j, i].value or 0.0)
                for (j, ii) in m.A if ii == i
            )
            flow_out = sum(
                float(m.y[k, i, j].value or 0.0)
                for (ii, j) in m.A if ii == i
            )
            # La demanda satisfecha es el flujo neto
            delivered = flow_in - flow_out
            if delivered > 1e-6:
                load += delivered

        cap = float(vehicles.set_index("id").loc[k, "Q"])
        veh_kpis.append({
            "vehicle": k,
            "distance_km": dist,
            "time_h": time,
            "cost": cost,
            "load_delivered": load,
            "capacity": cap,
        })
        
    pd.DataFrame(veh_kpis).to_csv(f"{DATA_DIR}/outputs/tables/vehicle_kpis.csv", index=False)

if __name__=="__main__":
    export_arcs_cache()
    m, msg = try_milp()
    if m is not None:
        export_solution(m)
    else:
        print("MILP not executed:", msg)
