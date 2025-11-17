
# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def make_mini_case(data_dir:str):
    data_dir = Path(data_dir)
    out_assets = data_dir/"report/assets"
    out_assets.mkdir(parents=True, exist_ok=True)

    arcs = pd.read_csv(data_dir/"outputs/tables/selected_arcs_detailed.csv")
    centers = pd.read_csv(data_dir/"data/raw/nodes_centers.csv")
    clients = pd.read_csv(data_dir/"data/raw/nodes_clients.csv")
    coord = pd.concat([centers[["id","lat","lon"]], clients[["id","lat","lon"]]]).set_index("id")

    # Elegimos un subconjunto simple: arcos donde aparece algún cliente {CL2, CL8} y algún CD
    # Si no existen en la solución, tomamos primeras 6 filas de arcs como demo.
    subset_clients = {"CL2","CL8"}
    sub = arcs[arcs["to"].isin(subset_clients) | arcs["from"].isin(subset_clients)].copy()
    if sub.empty:
        sub = arcs.head(6).copy()
    # Exportar arcos y totales
    sub[["vehicle","from","to","dist_km","time_h","cost"]].to_csv(out_assets/"caso_a_mano_arcos.csv", index=False)
    totales = sub.groupby("vehicle")[["dist_km","time_h","cost"]].sum().reset_index()
    totales.to_csv(out_assets/"caso_a_mano_totales.csv", index=False)

    # Figura prehecha (simple): dibujar nodos + esos arcos
    fig = plt.figure()
    plt.scatter(centers["lon"], centers["lat"], s=80, marker="s", label="CD")
    plt.scatter(clients["lon"], clients["lat"], s=30, marker="o", label="Clientes")
    for _,r in sub.iterrows():
        i, j = r["from"], r["to"]
        if i in coord.index and j in coord.index:
            x=[coord.loc[i,"lon"], coord.loc[j,"lon"]]
            y=[coord.loc[i,"lat"], coord.loc[j,"lat"]]
            plt.plot(x,y, linewidth=2)
    plt.xlabel("lon"); plt.ylabel("lat"); plt.legend()
    plt.title("Mini–caso: rutas ilustrativas")
    fig.savefig(out_assets/"caso_a_mano_prehecho.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
