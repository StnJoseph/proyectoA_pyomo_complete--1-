
# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def make_all_figures(data_dir:str):
    data_dir = Path(data_dir)
    out_fig = data_dir/"outputs/figures"
    out_fig.mkdir(parents=True, exist_ok=True)

    centers = pd.read_csv(data_dir/"data/raw/nodes_centers.csv")
    clients = pd.read_csv(data_dir/"data/raw/nodes_clients.csv")
    arcs = pd.read_csv(data_dir/"outputs/tables/selected_arcs_detailed.csv")
    flows = pd.read_csv(data_dir/"outputs/tables/flows_by_arc_per_vehicle.csv")
    center_kpis = pd.read_csv(data_dir/"outputs/tables/center_kpis.csv")
    vehicle_kpis = pd.read_csv(data_dir/"outputs/tables/vehicle_kpis.csv")

    # 01_nodes.png
    fig = plt.figure()
    plt.scatter(centers["lon"], centers["lat"], s=80, marker="s", label="CD")
    plt.scatter(clients["lon"], clients["lat"], s=30, marker="o", label="Clientes")
    for _,r in centers.iterrows():
        plt.text(r["lon"], r["lat"], r["id"])
    for _,r in clients.iterrows():
        plt.text(r["lon"], r["lat"], r["id"], fontsize=8)
    plt.xlabel("lon"); plt.ylabel("lat"); plt.legend()
    plt.title("Centros y clientes")
    fig.savefig(out_fig/"01_nodes.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # 02_routes_by_vehicle.png
    fig = plt.figure()
    # nodos base
    plt.scatter(centers["lon"], centers["lat"], s=80, marker="s", label="CD")
    plt.scatter(clients["lon"], clients["lat"], s=30, marker="o", label="Clientes")
    coord = pd.concat([centers[["id","lat","lon"]], clients[["id","lat","lon"]]])
    coord = coord.set_index("id")
    for _,r in arcs.iterrows():
        i, j = r["from"], r["to"]
        if i in coord.index and j in coord.index:
            x=[coord.loc[i,"lon"], coord.loc[j,"lon"]]
            y=[coord.loc[i,"lat"], coord.loc[j,"lat"]]
            plt.plot(x,y, linewidth=1)
    plt.xlabel("lon"); plt.ylabel("lat"); plt.legend()
    plt.title("Rutas por vehículo (trazos)")
    fig.savefig(out_fig/"02_routes_by_vehicle.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # 03_costs_per_vehicle.png
    fig = plt.figure()
    vehicle_kpis.sort_values("vehicle", inplace=True)
    plt.bar(vehicle_kpis["vehicle"], vehicle_kpis["cost"])
    plt.title("Costo por vehículo")
    fig.savefig(out_fig/"03_costs_per_vehicle.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # 04_supply_share.png
    fig = plt.figure()
    total = center_kpis["supply"].sum()
    share = (center_kpis.assign(share=lambda d: d["supply"]/total if total>0 else 0))
    plt.bar(share["center"], share["share"])
    plt.title("Participación de suministro por CD")
    fig.savefig(out_fig/"04_supply_share.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # 05_assignment_by_center.png (clientes por CD) — aproximado usando flujos entrantes
    # Proxy simple: contar cliente asignado al CD del primer arco entrante desde un CD
    if not arcs.empty:
        # Buscar arcos que entran a un cliente desde un CD
        assigned = []
        CDs = set(centers["id"].tolist())
        clients_ids = set(clients["id"].tolist())
        for _,r in arcs.iterrows():
            i, j = r["from"], r["to"]
            if (i in CDs) and (j in clients_ids):
                assigned.append((i,j))
        df = pd.DataFrame(assigned, columns=["center","client"])
        count = df.groupby("center").size().reset_index(name="n_clients")
    else:
        count = pd.DataFrame({"center": centers["id"], "n_clients": 0})
    fig = plt.figure()
    plt.bar(count["center"], count["n_clients"])
    plt.title("Clientes por CD")
    fig.savefig(out_fig/"05_assignment_by_center.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # 06_flow_by_arc_total.png
    fig = plt.figure()
    if not flows.empty:
        flows_sum = flows.groupby(["from","to"])["flow"].sum().reset_index()
        plt.bar(range(len(flows_sum)), flows_sum["flow"])
        plt.title("Flujo total por arco")
    else:
        plt.bar([0],[0]); plt.title("Flujo total por arco (sin datos)")
    fig.savefig(out_fig/"06_flow_by_arc_total.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # 07_flow_by_arc_per_vehicle.png
    fig = plt.figure()
    if not flows.empty:
        flows_k = flows.groupby(["vehicle"])["flow"].sum().reset_index()
        plt.bar(flows_k["vehicle"], flows_k["flow"])
        plt.title("Flujo por vehículo")
    else:
        plt.bar([0],[0]); plt.title("Flujo por vehículo (sin datos)")
    fig.savefig(out_fig/"07_flow_by_arc_per_vehicle.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # 08_center_capacity_util.png
    fig = plt.figure()
    center_kpis["util_pct"] = (center_kpis["utilization"]*100).clip(lower=0, upper=100)
    plt.bar(center_kpis["center"], center_kpis["util_pct"])
    plt.title("Utilización de capacidad (%) por CD")
    fig.savefig(out_fig/"08_center_capacity_util.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # 10_vehicle_load_util.png
    fig = plt.figure()
    # load/capacity
    vehicle_kpis["load_util"] = (vehicle_kpis["load_delivered"]/vehicle_kpis["capacity"]).replace([float('inf')], 0).fillna(0)
    plt.bar(vehicle_kpis["vehicle"], vehicle_kpis["load_util"]*100)
    plt.title("Utilización de carga (%) por vehículo")
    fig.savefig(out_fig/"10_vehicle_load_util.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # 11_cost_breakdown_per_vehicle.png — usamos costo total (ya incluye combustible+tiempo).
    fig = plt.figure()
    plt.bar(vehicle_kpis["vehicle"], vehicle_kpis["cost"])
    plt.title("Desglose de costos por vehículo (total)")
    fig.savefig(out_fig/"11_cost_breakdown_per_vehicle.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

