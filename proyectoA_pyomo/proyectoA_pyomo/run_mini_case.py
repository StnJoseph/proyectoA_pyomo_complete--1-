
# run_mini_case.py
# Produces ALL CSV outputs required by the LaTeX, without relying on external solvers.
# - reads inputs from proyectoA_pyomo/inputs
# - writes outputs to proyectoA_pyomo/outputs/tables and report/assets
import os, math, itertools
import pandas as pd

ROOT = os.path.dirname(__file__)
INP = os.path.join(ROOT, "inputs")
OUT_TAB = os.path.join(ROOT, "outputs", "tables")
ASSETS = os.path.join(ROOT, "report", "assets")
os.makedirs(OUT_TAB, exist_ok=True); os.makedirs(ASSETS, exist_ok=True)

centers = pd.read_csv(os.path.join(INP,"nodes_centers.csv"))
clients = pd.read_csv(os.path.join(INP,"nodes_clients.csv"))
vehicles = pd.read_csv(os.path.join(INP,"vehicles.csv"))
econ = pd.read_csv(os.path.join(INP,"economics.csv"))
access = pd.read_csv(os.path.join(INP,"access.csv"))

fuel_price = float(econ["fuel_price"].iloc[0])

# Build arc table quickly from coordinates (same as preprocess but small)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2-lat1)
    dl = math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

alpha = float(econ.get("alpha", pd.Series([1.25])).iloc[0])

nodes = pd.concat([centers[["id","lat","lon"]], clients[["id","lat","lon"]]], ignore_index=True)
id2coord = {r.id:(r.lat, r.lon) for _,r in nodes.iterrows()}

arcs = {}
for i in id2coord:
    for j in id2coord:
        if i==j: continue
        (la,lo),(lb,lblo)=id2coord[i], id2coord[j]
        d = haversine(la,lo,lb,lblo)*alpha
        t = d/25.0  # 25 km/h
        arcs[(i,j)] = {"dist":d, "time":t}

# Access map
acc = {(row.node_id, row.veh_id): int(row.allowed) for _,row in access.iterrows()}

# Data helpers
C = list(centers["id"])
I = list(clients["id"])
K = list(vehicles["id"])
q = {r.id: float(r.q) for _,r in clients.iterrows()}
cap_c = {r.id: float(r.cap_c) for _,r in centers.iterrows()}

veh = {}
for _,r in vehicles.iterrows():
    veh[r.id] = dict(Q=float(r.Q), R=float(r.R), eff=float(r.eff),
                     w_time=float(r.w_time), c_km=float(r.c_km),
                     f_fixed=float(r.f_fixed), Tmax=float(r.Tmax))

# Feasible partitions of clients into vehicles (tiny set -> brute force)
def partitions(lst, k):
    # yield dict: veh_id -> list_of_clients
    for grouping in itertools.product(range(k), repeat=len(lst)):
        buckets = {i:[] for i in range(k)}
        for cidx, b in enumerate(grouping):
            buckets[b].append(lst[cidx])
        yield buckets

best = None

def route_cost(route, k):
    # route like [CD, c1, c2, ..., CD]
    tot_dist=0.0; tot_time=0.0
    for i,j in zip(route[:-1], route[1:]):
        a = arcs[(i,j)]
        tot_dist += a["dist"]; tot_time += a["time"]
    fuel = fuel_price * (tot_dist / (veh[k]["eff"]+1e-9))
    timec = veh[k]["w_time"] * tot_time
    kmc   = veh[k]["c_km"] * tot_dist
    return fuel + timec + kmc, tot_dist, tot_time

def all_permutations(clients_sub):
    if not clients_sub: 
        return [[]]
    return itertools.permutations(clients_sub)

CD = C[0]  # single center in the mini-case

for assign in partitions(I, len(K)):
    # Capacity and access feasibility quick check
    ok_assign = True
    for idx,k in enumerate(K):
        assigned = assign[idx]
        if sum(q[c] for c in assigned) > veh[k]["Q"] + 1e-9:
            ok_assign = False; break
    if not ok_assign:
        continue

    # Build routes and compute cost
    total_cost=0.0; details=[]
    feasible=True
    for idx,k in enumerate(K):
        assigned = assign[idx]
        if not assigned:
            # inactive vehicle: only fixed cost if we count activation; here activate only if used
            continue
        best_k = None
        for perm in all_permutations(assigned):
            route = [CD] + list(perm) + [CD]
            # access feasibility
            access_ok = True
            for i,j in zip(route[:-1], route[1:]):
                if (i,k) in acc and acc[(i,k)]==0: access_ok=False; break
                if (j,k) in acc and acc[(j,k)]==0: access_ok=False; break
            if not access_ok: 
                continue
            cost,dist,time = route_cost(route, k)
            if dist > veh[k]["R"] + 1e-9: 
                continue
            if time > veh[k]["Tmax"] + 1e-9:
                continue
            if best_k is None or cost < best_k[0]:
                best_k = (cost, route, dist, time)
        if best_k is None:
            feasible=False; break
        total_cost += best_k[0] + veh[k]["f_fixed"]
        details.append((k, best_k[1], best_k[0], best_k[2], best_k[3], sum(q[c] for c in assigned)))
    if not feasible:
        continue
    if (best is None) or (total_cost < best[0]):
        best = (total_cost, details, assign)

# Export outputs
sel_rows=[]; flow_rows=[]; veh_rows=[]; center_rows=[]
mini_arcos=[]; mini_totales=[]

if best is None:
    raise RuntimeError("No feasible mini-case found. Check input parameters.")

total_cost, details, assign = best
total_supply = sum(q[c] for c in I)
center_rows.append({"center":CD,"supply":total_supply,"cap":cap_c[CD]})

for (k, route, cost, dist, time, load_sum) in details:
    # Selected arcs
    for i,j in zip(route[:-1], route[1:]):
        a = arcs[(i,j)]
        sel_rows.append({"vehicle":k,"i":i,"j":j,"dist_km":a["dist"],"time_h":a["time"],"flow":0.0})

        # mini-case arc costs
        fuel = fuel_price * (a["dist"]/(veh[k]["eff"]+1e-9))
        timec = veh[k]["w_time"]*a["time"]
        kmc = veh[k]["c_km"]*a["dist"]
        mini_arcos.append({
            "vehicle":k,"i":i,"j":j,"dist_km":a["dist"],"time_h":a["time"],
            "fuel_cost":fuel,"time_cost":timec,"km_cost":kmc,"total_cost":fuel+timec+kmc
        })

    # Compute flows along route: departing CD carries sum(q of remaining clients)
    remaining = {c:q[c] for c in route if c in q}
    flow_by_arc=[]
    current_load = sum(remaining.values())
    for i,j in zip(route[:-1], route[1:]):
        a = arcs[(i,j)]
        flow_by_arc.append((i,j,current_load))
        if j in remaining:
            current_load -= remaining[j]  # delivered at arrival to client

    for (i,j,fl) in flow_by_arc:
        flow_rows.append({"vehicle":k,"i":i,"j":j,"flow":fl})

    veh_rows.append({
        "vehicle":k,"active":1,"dist_used_km":dist,"R_km":veh[k]["R"],
        "time_used_h":time,"Tmax_h":veh[k]["Tmax"],
        "load_sum":load_sum,"Q":veh[k]["Q"]
    })

    mini_totales.append({
        "vehicle":k, "total_dist_km":dist, "total_time_h":time, "total_cost":cost
    })

# Save CSVs required by LaTeX
pd.DataFrame(sel_rows).to_csv(os.path.join(OUT_TAB,"selected_arcs_detailed.csv"), index=False)
pd.DataFrame(flow_rows).to_csv(os.path.join(OUT_TAB,"flows_by_arc_per_vehicle.csv"), index=False)
pd.DataFrame(center_rows).to_csv(os.path.join(OUT_TAB,"center_kpis.csv"), index=False)
pd.DataFrame(veh_rows).to_csv(os.path.join(OUT_TAB,"vehicle_kpis.csv"), index=False)

# Mini-caso assets
pd.DataFrame(mini_arcos).to_csv(os.path.join(ASSETS,"caso_a_mano_arcos.csv"), index=False)
pd.DataFrame(mini_totales).to_csv(os.path.join(ASSETS,"caso_a_mano_totales.csv"), index=False)

print("OK mini-case: CSVs exported to outputs/tables and report/assets")
