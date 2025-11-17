
# pipelines/preprocess.py
# This is a placeholder with a clean contract:
# - Reads inputs in proyectoA_pyomo/inputs
# - Writes arcs.csv and copies nodes_* to outputs/tables
# - Computes distances (Haversine * alpha) and times based on a default speed profile
import math, os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(__file__))
INP = os.path.join(ROOT, "inputs")
OUT_TAB = os.path.join(ROOT, "outputs", "tables")

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2-lat1)
    dl = math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

def run(alpha=1.25, v_kmh=25.0):
    os.makedirs(OUT_TAB, exist_ok=True)
    centers = pd.read_csv(os.path.join(INP,"nodes_centers.csv"))
    clients = pd.read_csv(os.path.join(INP,"nodes_clients.csv"))
    econ = pd.read_csv(os.path.join(INP,"economics.csv"))
    if "alpha" in econ.columns:
        alpha = float(econ["alpha"].iloc[0])

    nodes = pd.concat([centers[["id","lat","lon"]], clients[["id","lat","lon"]]], ignore_index=True)
    # full digraph except self-loops
    arcs=[]
    for i in range(len(nodes)):
        for j in range(len(nodes)):
            if i==j: continue
            ni, nj = nodes.iloc[i], nodes.iloc[j]
            d = haversine(ni.lat, ni.lon, nj.lat, nj.lon)*alpha
            t = d / v_kmh
            arcs.append({"i":ni.id,"j":nj.id,"dist":d,"time":t,"habilitado":1})
    arcs_df = pd.DataFrame(arcs)
    arcs_df.to_csv(os.path.join(OUT_TAB,"arcs.csv"), index=False)
    centers.to_csv(os.path.join(OUT_TAB,"nodes_centers.csv"), index=False)
    clients.to_csv(os.path.join(OUT_TAB,"nodes_clients.csv"), index=False)

if __name__=="__main__":
    run()
