
# run_full.py
# If Pyomo and a MILP solver are available, this script uses model/build_model.py to solve the full instance.
# Otherwise, it fails gracefully and asks to install pyomo + a solver (glpk/cbc/gurobi).
import os, sys, importlib, pandas as pd

ROOT = os.path.dirname(__file__)
sys.path.append(os.path.join(ROOT,"model"))
from build_model import build_model

def read_inputs():
    INP = os.path.join(ROOT, "inputs")
    centers = pd.read_csv(os.path.join(INP,"nodes_centers.csv"))
    clients = pd.read_csv(os.path.join(INP,"nodes_clients.csv"))
    vehicles = pd.read_csv(os.path.join(INP,"vehicles.csv"))
    econ = pd.read_csv(os.path.join(INP,"economics.csv"))
    access = pd.read_csv(os.path.join(INP,"access.csv"))
    arcs = pd.read_csv(os.path.join(ROOT,"outputs","tables","arcs.csv")) \
            if os.path.exists(os.path.join(ROOT,"outputs","tables","arcs.csv")) \
            else None
    return centers, clients, vehicles, econ, access, arcs

def to_data(centers, clients, vehicles, econ, access, arcs):
    C = list(centers["id"])
    I = list(clients["id"])
    K = list(vehicles["id"])

    data = {}
    data['C'], data['I'], data['K'] = C, I, K

    if arcs is None:
        raise RuntimeError("arcs.csv not found. Run pipelines/preprocess.py first.")
    A = list(zip(arcs["i"], arcs["j"]))
    data['A'] = A
    data['dist'] = {(r.i, r.j): float(r.dist) for _,r in arcs.iterrows()}
    data['time'] = {(r.i, r.j): float(r.time) for _,r in arcs.iterrows()}

    data['q'] = {r.id: float(r.q) for _,r in clients.iterrows()}
    data['cap_c'] = {r.id: float(r.cap_c) for _,r in centers.iterrows()}

    data['Q'] = {r.id: float(r.Q) for _,r in vehicles.iterrows()}
    data['A_access'] = {(row.node_id,row.veh_id): int(row.allowed) for _,row in access.iterrows()}
    data['fuel_price'] = float(econ["fuel_price"].iloc[0])
    data['eff_k'] = {r.id: float(r.eff) for _,r in vehicles.iterrows()}
    data['w_time'] = {r.id: float(r.w_time) for _,r in vehicles.iterrows()}
    data['c_km'] = {r.id: float(r.c_km) for _,r in vehicles.iterrows()}
    data['f_fixed'] = {r.id: float(r.f_fixed) for _,r in vehicles.iterrows()}
    data['range_k'] = {r.id: float(r.R) for _,r in vehicles.iterrows()}
    data['Tmax_k'] = {r.id: float(r.Tmax) for _,r in vehicles.iterrows()}
    return data

def export_solution(m):
    import pandas as pd
    from pyomo.environ import value
    OUT_TAB = os.path.join(ROOT, "outputs", "tables")
    os.makedirs(OUT_TAB, exist_ok=True)

    sel=[]; flows=[]; ckp=[]; vkp=[]
    for k in m.K:
        for (i,j) in m.A:
            if value(m.x[k,i,j])>0.5:
                sel.append({"vehicle":k,"i":i,"j":j,
                            "dist_km":value(m.dist[i,j]),"time_h":value(m.tt[i,j]),
                            "flow":value(m.y[k,i,j])})
            flows.append({"vehicle":k,"i":i,"j":j,"flow":value(m.y[k,i,j])})
    for c in m.C:
        ckp.append({"center":c,"supply":value(m.s[c]),"cap":value(m.cap_c[c])})
    for k in m.K:
        dist = sum(value(m.dist[i,j])*value(m.x[k,i,j]) for (i,j) in m.A)
        ttot = sum(value(m.tt[i,j])*value(m.x[k,i,j]) for (i,j) in m.A)
        load = sum(value(m.y[k,i,j]) for (i,j) in m.A)
        vkp.append({"vehicle":k,"active":int(value(m.u[k])>0.5),
                    "dist_used_km":dist,"R_km":value(m.R[k]),
                    "time_used_h":ttot,"Tmax_h":value(m.Tmax[k]),
                    "load_sum":load,"Q":value(m.Q[k])})

    pd.DataFrame(sel).to_csv(os.path.join(OUT_TAB,"selected_arcs_detailed.csv"), index=False)
    pd.DataFrame(flows).to_csv(os.path.join(OUT_TAB,"flows_by_arc_per_vehicle.csv"), index=False)
    pd.DataFrame(ckp).to_csv(os.path.join(OUT_TAB,"center_kpis.csv"), index=False)
    pd.DataFrame(vkp).to_csv(os.path.join(OUT_TAB,"vehicle_kpis.csv"), index=False)

if __name__=="__main__":
    try:
        from pyomo.environ import SolverFactory
    except Exception as e:
        raise SystemExit("Pyomo is not installed. Please install pyomo and a MILP solver (e.g., glpk).")

    centers, clients, vehicles, econ, access, arcs = read_inputs()
    data = to_data(centers, clients, vehicles, econ, access, arcs)
    m = build_model(data)

    # Choose a solver
    for cand in ['glpk','cbc','gurobi']:
        try:
            solver = SolverFactory(cand)
            if solver.available():
                chosen = cand; break
        except:
            continue
    else:
        raise SystemExit("No MILP solver available. Install glpk or cbc or configure gurobi.")

    res = solver.solve(m, tee=False)
    export_solution(m)
    print("OK full: CSVs exported to outputs/tables")
