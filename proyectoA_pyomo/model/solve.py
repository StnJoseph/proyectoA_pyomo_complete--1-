
import os, json, pandas as pd, numpy as np
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
        for s in ["glpk","cbc","highs"]:
            if SolverFactory(s).available(exception_flag=False):
                solver = SolverFactory(s)
                break
        if solver is None:
            return None, "No solver available"
        res = solver.solve(m, tee=False)
        status = str(res.solver.status)
        if "ok" not in status.lower() and "optimal" not in str(res.solver.termination_condition).lower():
            return None, f"Solver status: {status}"
        return m, "OK"
    except Exception as e:
        return None, f"MILP error: {e}"

def export_solution(m):
    # Read input frames
    centers = pd.read_csv(f"{DATA_DIR}/data/raw/nodes_centers.csv")
    clients = pd.read_csv(f"{DATA_DIR}/data/raw/nodes_clients.csv")
    vehicles = pd.read_csv(f"{DATA_DIR}/data/params/vehicles.csv")
    # Export x arcs
    sel = []
    for k in m.K:
        for (i,j) in m.A:
            if m.x[k,i,j].value and m.x[k,i,j].value > 0.5:
                sel.append({"vehicle":k, "from":i, "to":j})
    sel_df = pd.DataFrame(sel)
    # fetch cost/time/dist from cache
    arcs_df = pd.read_csv(f"{DATA_DIR}/outputs/tables/arcs_cache.csv")
    sel_df = sel_df.merge(arcs_df.rename(columns={"veh":"vehicle"}), on=["vehicle","i","j"], how="left").rename(columns={"i":"from","j":"to"})
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
        cap = float(centers.set_index("id").loc[c,"cap"])
        center_kpis.append({"center":c,"supply":s,"cap":cap,"utilization": s/cap if cap>0 else 0})
    pd.DataFrame(center_kpis).to_csv(f"{DATA_DIR}/outputs/tables/center_kpis.csv", index=False)

    # KPIs vehicles
    veh_kpis = []
    for k in m.K:
        dist = sum(float(m.dist[k,i,j]) * (1 if (m.x[k,i,j].value and m.x[k,i,j].value>0.5) else 0) for (i,j) in m.A)
        # recompute time+cost from arcs cache
        sub = arcs_df[(arcs_df["veh"]==k) & (arcs_df.apply(lambda r: int(m.x[k,r["i"],r["j"]].value>0.5) if (k,r["i"],r["j"]) else 0, axis=1))]
        time = sub["time_h"].sum()
        cost = sub["cost"].sum()
        load = sum(float(m.y[k,i,j].value) for (i,j) in m.A if (m.y[k,i,j].value or 0)>1e-6 and j in m.I)
        cap = float(vehicles.set_index("id").loc[k,"Q"])
        veh_kpis.append({"vehicle":k,"distance_km":dist,"time_h":time,"cost":cost,"load_delivered":load,"capacity":cap})
    pd.DataFrame(veh_kpis).to_csv(f"{DATA_DIR}/outputs/tables/vehicle_kpis.csv", index=False)

if __name__=="__main__":
    export_arcs_cache()
    m, msg = try_milp()
    if m is not None:
        export_solution(m)
    else:
        print("MILP not executed:", msg)
