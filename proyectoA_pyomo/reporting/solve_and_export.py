
# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
from pyomo.environ import SolverFactory, value
from model.build_model import build_model

def solve_and_export(data_dir:str):
    data_dir = Path(data_dir)
    out_tables = data_dir/"outputs/tables"
    out_tables.mkdir(parents=True, exist_ok=True)

    m = build_model(str(data_dir))

    solver = None
    for s in ["highs","cbc","glpk"]:
        try:
            if SolverFactory(s).available(exception_flag=False):
                solver = SolverFactory(s)
                break
        except Exception:
            pass
    if solver is None:
        raise RuntimeError("No solver available (instala HiGHS/CB C/GLPK).")

    res = solver.solve(m, tee=False)
    term = str(getattr(res.solver, "termination_condition", ""))
    if "optimal" not in term.lower():
        raise RuntimeError(f"Solver terminó con: {term}")

    # Exportar arcos seleccionados
    arcs_cache = pd.read_csv(out_tables/"arcs_cache.csv")
    sel = []
    for k in m.K:
        for (i,j) in m.A:
            xv = m.x[k,i,j].value
            if xv is not None and xv > 0.5:
                sel.append({"vehicle":k,"from":i,"to":j})
    sel_df = pd.DataFrame(sel)
    if sel_df.empty:
        # Generar CSVs vacíos con columnas esperadas
        sel_df = pd.DataFrame(columns=["vehicle","from","to","dist_km","time_h","cost"])
    else:
        sel_df = sel_df.merge(arcs_cache, on=["vehicle","from","to"], how="left", validate="m:1")
    sel_df.to_csv(out_tables/"selected_arcs_detailed.csv", index=False)

    # Flujos por arco y vehículo
    flows = []
    for k in m.K:
        for (i,j) in m.A:
            yv = m.y[k,i,j].value
            yv = float(yv) if yv is not None else 0.0
            if yv > 1e-6:
                flows.append({"vehicle":k,"from":i,"to":j,"flow":yv})
    pd.DataFrame(flows).to_csv(out_tables/"flows_by_arc_per_vehicle.csv", index=False)

    # KPIs centros
    centers = pd.read_csv(data_dir/"data/raw/nodes_centers.csv").set_index("id")
    center_kpis = []
    for c in m.C:
        s_val = float(m.s[c].value) if m.s[c].value is not None else 0.0
        cap = float(centers.loc[c,"cap"]) if c in centers.index else float("nan")
        util = (s_val/cap) if cap>0 else float("nan")
        center_kpis.append({"center":c,"supply":s_val,"cap":cap,"utilization":util})
    pd.DataFrame(center_kpis).to_csv(out_tables/"center_kpis.csv", index=False)

    # KPIs vehículos
    vehicles = pd.read_csv(data_dir/"data/params/vehicles.csv").set_index("id")
    veh_kpis = []
    for k in m.K:
        sub = sel_df[sel_df["vehicle"]==k]
        dist = float(sub["dist_km"].sum()) if not sub.empty else 0.0
        time = float(sub["time_h"].sum()) if not sub.empty else 0.0
        cost = float(sub["cost"].sum()) if not sub.empty else 0.0
        # carga entregada a clientes (entradas a clientes)
        load = 0.0
        for (i,j) in m.A:
            if j in m.I:
                v = m.y[k,i,j].value
                load += float(v) if v is not None else 0.0
        cap = float(vehicles.loc[k,"Q"]) if k in vehicles.index else float("nan")
        veh_kpis.append({
            "vehicle":k, "distance_km":dist, "time_h":time, "cost":cost,
            "load_delivered":load, "capacity":cap
        })
    pd.DataFrame(veh_kpis).to_csv(out_tables/"vehicle_kpis.csv", index=False)

    return True
