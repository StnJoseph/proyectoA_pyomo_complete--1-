# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración de estilo
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10

def make_all_figures(data_dir: str):
    """
    Genera todas las figuras de análisis para un caso específico.
    
    Args:
        data_dir: Ruta al directorio raíz del proyecto
    """
    data_dir = Path(data_dir)
    out_fig = data_dir / "outputs" / "figures"
    out_fig.mkdir(parents=True, exist_ok=True)

    # ====================================================================
    # LECTURA DE DATOS (RUTAS CORREGIDAS)
    # ====================================================================
    
    # Leer desde inputs/ (datos preprocesados)
    centers = pd.read_csv(data_dir / "inputs" / "nodes_centers.csv")
    clients = pd.read_csv(data_dir / "inputs" / "nodes_clients.csv")
    
    # Leer desde outputs/tables/ (resultados del solver)
    arcs = pd.read_csv(data_dir / "outputs" / "tables" / "selected_arcs_detailed.csv")
    flows = pd.read_csv(data_dir / "outputs" / "tables" / "flows_by_arc_per_vehicle.csv")
    center_kpis = pd.read_csv(data_dir / "outputs" / "tables" / "center_kpis.csv")
    vehicle_kpis = pd.read_csv(data_dir / "outputs" / "tables" / "vehicle_kpis.csv")

    # Coordenadas de todos los nodos
    coord = pd.concat([
        centers[["id", "lat", "lon"]],
        clients[["id", "lat", "lon"]]
    ]).set_index("id")

    print(f" Generando figuras en: {out_fig}")

    # ====================================================================
    # FIGURA 1: MAPA DE NODOS
    # ====================================================================
    fig, ax = plt.subplots(figsize=(12, 8))
    
    ax.scatter(centers["lon"], centers["lat"], s=200, marker="s", 
               color='red', label="Centros de Distribución", zorder=3, edgecolors='black', linewidth=2)
    ax.scatter(clients["lon"], clients["lat"], s=80, marker="o", 
               color='steelblue', label="Clientes", zorder=2, alpha=0.7)
    
    # Etiquetas
    for _, r in centers.iterrows():
        ax.text(r["lon"], r["lat"], r["id"], fontsize=10, fontweight='bold',
                ha='center', va='bottom', bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    for _, r in clients.iterrows():
        ax.text(r["lon"], r["lat"], r["id"], fontsize=7, ha='center', va='bottom')
    
    ax.set_xlabel("Longitud", fontsize=12)
    ax.set_ylabel("Latitud", fontsize=12)
    ax.set_title("Mapa de Centros de Distribución y Clientes", fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='best')
    ax.grid(True, alpha=0.3)
    
    fig.savefig(out_fig / "01_nodes.png", bbox_inches="tight")
    plt.close(fig)
    print("01_nodes.png")

    # ====================================================================
    # FIGURA 2: RUTAS POR VEHÍCULO
    # ====================================================================
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Nodos base
    ax.scatter(centers["lon"], centers["lat"], s=200, marker="s", 
               color='red', label="CD", zorder=3, edgecolors='black', linewidth=2)
    ax.scatter(clients["lon"], clients["lat"], s=60, marker="o", 
               color='lightgray', label="Clientes", zorder=1, alpha=0.5)
    
    # Rutas por vehículo (cada vehículo con color diferente)
    vehicles = arcs["vehicle"].unique()
    colors = plt.cm.tab10(range(len(vehicles)))
    
    for idx, veh in enumerate(vehicles):
        veh_arcs = arcs[arcs["vehicle"] == veh]
        color = colors[idx]
        
        for _, r in veh_arcs.iterrows():
            i, j = r["from"], r["to"]
            if i in coord.index and j in coord.index:
                x = [coord.loc[i, "lon"], coord.loc[j, "lon"]]
                y = [coord.loc[i, "lat"], coord.loc[j, "lat"]]
                ax.plot(x, y, linewidth=2, color=color, alpha=0.7, label=veh if _ == 0 else "")
    
    ax.set_xlabel("Longitud", fontsize=12)
    ax.set_ylabel("Latitud", fontsize=12)
    ax.set_title("Rutas Óptimas por Vehículo", fontsize=14, fontweight='bold')
    
    # Leyenda solo con vehículos únicos
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), fontsize=9, loc='best')
    ax.grid(True, alpha=0.3)
    
    fig.savefig(out_fig / "02_routes_by_vehicle.png", bbox_inches="tight")
    plt.close(fig)
    print("02_routes_by_vehicle.png")

    # ====================================================================
    # FIGURA 3: COSTOS POR VEHÍCULO
    # ====================================================================
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Filtrar vehículos activos
    active_veh = vehicle_kpis[vehicle_kpis["cost"] > 0].sort_values("cost", ascending=False)
    
    if not active_veh.empty:
        colors_bar = ['green' if c < active_veh["cost"].median() else 'orange' 
                      for c in active_veh["cost"]]
        
        ax.barh(active_veh["vehicle"], active_veh["cost"], color=colors_bar)
        ax.set_xlabel("Costo Total (COP)", fontsize=12)
        ax.set_ylabel("Vehículo", fontsize=12)
        ax.set_title("Costo Operativo por Vehículo", fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        
        # Añadir valores
        for idx, row in active_veh.iterrows():
            ax.text(row["cost"], row["vehicle"], f' ${row["cost"]:,.0f}', 
                    va='center', fontsize=9)
    else:
        ax.text(0.5, 0.5, 'No hay vehículos activos', ha='center', va='center')
    
    fig.savefig(out_fig / "03_costs_per_vehicle.png", bbox_inches="tight")
    plt.close(fig)
    print("03_costs_per_vehicle.png")

    # ====================================================================
    # FIGURA 4: PARTICIPACIÓN DE SUMINISTRO POR CD
    # ====================================================================
    fig, ax = plt.subplots(figsize=(10, 6))
    
    total_supply = center_kpis["supply"].sum()
    if total_supply > 0:
        center_kpis["share"] = (center_kpis["supply"] / total_supply) * 100
        
        ax.bar(center_kpis["center"], center_kpis["share"], color='steelblue', edgecolor='black')
        ax.set_xlabel("Centro de Distribución", fontsize=12)
        ax.set_ylabel("Participación (%)", fontsize=12)
        ax.set_title("Participación de Suministro por Centro", fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Valores encima de barras
        for idx, row in center_kpis.iterrows():
            ax.text(row["center"], row["share"], f'{row["share"]:.1f}%', 
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
    else:
        ax.text(0.5, 0.5, 'No hay suministro registrado', ha='center', va='center')
    
    fig.savefig(out_fig / "04_supply_share.png", bbox_inches="tight")
    plt.close(fig)
    print("04_supply_share.png")

    # ====================================================================
    # FIGURA 5: CLIENTES ATENDIDOS POR CD
    # ====================================================================
    fig, ax = plt.subplots(figsize=(10, 6))
    
    CDs = set(centers["id"].tolist())
    clients_ids = set(clients["id"].tolist())
    
    if not arcs.empty:
        # Arcos desde CD hacia cliente
        cd_to_client = arcs[
            arcs["from"].isin(CDs) & arcs["to"].isin(clients_ids)
        ].copy()
        
        if not cd_to_client.empty:
            count = cd_to_client.groupby("from").size().reset_index(name="n_clients")
            count.columns = ["center", "n_clients"]
            
            ax.bar(count["center"], count["n_clients"], color='coral', edgecolor='black')
            ax.set_xlabel("Centro de Distribución", fontsize=12)
            ax.set_ylabel("Número de Clientes", fontsize=12)
            ax.set_title("Clientes Atendidos por Centro", fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='y')
            
            # Valores
            for idx, row in count.iterrows():
                ax.text(row["center"], row["n_clients"], str(int(row["n_clients"])), 
                        ha='center', va='bottom', fontsize=11, fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'No hay asignaciones CD → Cliente', ha='center', va='center')
    else:
        ax.text(0.5, 0.5, 'No hay rutas disponibles', ha='center', va='center')
    
    fig.savefig(out_fig / "05_assignment_by_center.png", bbox_inches="tight")
    plt.close(fig)
    print("05_assignment_by_center.png")

    # ====================================================================
    # FIGURA 6: FLUJO TOTAL POR ARCO
    # ====================================================================
    fig, ax = plt.subplots(figsize=(12, 6))
    
    if not flows.empty:
        flows_sum = flows.groupby(["from", "to"])["flow"].sum().reset_index()
        flows_sum = flows_sum.sort_values("flow", ascending=False).head(20)  # Top 20
        
        flows_sum["arc"] = flows_sum["from"] + "→" + flows_sum["to"]
        
        ax.barh(flows_sum["arc"], flows_sum["flow"], color='teal')
        ax.set_xlabel("Flujo (unidades)", fontsize=12)
        ax.set_ylabel("Arco", fontsize=12)
        ax.set_title("Top 20 Arcos por Flujo Total", fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
    else:
        ax.text(0.5, 0.5, 'No hay flujos registrados', ha='center', va='center')
    
    fig.savefig(out_fig / "06_flow_by_arc_total.png", bbox_inches="tight")
    plt.close(fig)
    print("06_flow_by_arc_total.png")

    # ====================================================================
    # FIGURA 7: FLUJO POR VEHÍCULO
    # ====================================================================
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if not flows.empty:
        flows_k = flows.groupby("vehicle")["flow"].sum().reset_index()
        flows_k = flows_k.sort_values("flow", ascending=False)
        
        ax.bar(flows_k["vehicle"], flows_k["flow"], color='purple', edgecolor='black')
        ax.set_xlabel("Vehículo", fontsize=12)
        ax.set_ylabel("Flujo Total (unidades)", fontsize=12)
        ax.set_title("Carga Total Transportada por Vehículo", fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Valores
        for idx, row in flows_k.iterrows():
            ax.text(row["vehicle"], row["flow"], f'{row["flow"]:.0f}', 
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
    else:
        ax.text(0.5, 0.5, 'No hay flujos por vehículo', ha='center', va='center')
    
    fig.savefig(out_fig / "07_flow_by_arc_per_vehicle.png", bbox_inches="tight")
    plt.close(fig)
    print("07_flow_by_arc_per_vehicle.png")

    # ====================================================================
    # FIGURA 8: UTILIZACIÓN DE CAPACIDAD POR CD
    # ====================================================================
    fig, ax = plt.subplots(figsize=(10, 6))
    
    center_kpis["util_pct"] = (center_kpis["utilization"] * 100).clip(lower=0, upper=100)
    
    colors_util = ['green' if u > 70 else 'yellow' if u > 40 else 'red' 
                   for u in center_kpis["util_pct"]]
    
    ax.bar(center_kpis["center"], center_kpis["util_pct"], color=colors_util, edgecolor='black')
    ax.set_xlabel("Centro de Distribución", fontsize=12)
    ax.set_ylabel("Utilización (%)", fontsize=12)
    ax.set_title("Utilización de Capacidad por Centro", fontsize=14, fontweight='bold')
    ax.axhline(y=70, color='green', linestyle='--', alpha=0.5, label='Objetivo: 70%')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Valores
    for idx, row in center_kpis.iterrows():
        ax.text(row["center"], row["util_pct"], f'{row["util_pct"]:.1f}%', 
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    fig.savefig(out_fig / "08_center_capacity_util.png", bbox_inches="tight")
    plt.close(fig)
    print("08_center_capacity_util.png")

    # ====================================================================
    # FIGURA 9: DESGLOSE DE COSTOS (PIE CHART)
    # ====================================================================
    fig, ax = plt.subplots(figsize=(10, 8))
    
    if all(col in arcs.columns for col in ["fuel_cost", "dist_cost", "time_cost"]):
        fuel_total = arcs["fuel_cost"].sum()
        dist_total = arcs["dist_cost"].sum()
        time_total = arcs["time_cost"].sum()
        
        labels = ['Combustible', 'Distancia\n(mantenimiento)', 'Tiempo\n(mano de obra)']
        sizes = [fuel_total, dist_total, time_total]
        colors_pie = ['#ff6b6b', '#4ecdc4', '#45b7d1']
        explode = (0.05, 0, 0)
        
        ax.pie(sizes, explode=explode, labels=labels, colors=colors_pie, 
               autopct='%1.1f%%', shadow=True, startangle=90, textprops={'fontsize': 12})
        ax.axis('equal')
        ax.set_title("Desglose de Costos Operativos", fontsize=16, fontweight='bold', pad=20)
        
        # Leyenda con valores
        legend_labels = [f"{label}: ${size:,.0f} COP" for label, size in zip(labels, sizes)]
        ax.legend(legend_labels, loc="upper left", bbox_to_anchor=(1, 1), fontsize=10)
    else:
        ax.text(0.5, 0.5, 'Componentes de costo no disponibles', ha='center', va='center')
    
    fig.savefig(out_fig / "09_cost_breakdown_pie.png", bbox_inches="tight")
    plt.close(fig)
    print("09_cost_breakdown_pie.png")

    # ====================================================================
    # FIGURA 10: UTILIZACIÓN DE CARGA POR VEHÍCULO
    # ====================================================================
    fig, ax = plt.subplots(figsize=(10, 6))
    
    vehicle_kpis["load_util"] = (
        vehicle_kpis["load_delivered"] / vehicle_kpis["capacity"]
    ).replace([float('inf')], 0).fillna(0) * 100
    
    active_load = vehicle_kpis[vehicle_kpis["load_util"] > 0].sort_values("load_util", ascending=False)
    
    if not active_load.empty:
        colors_load = ['green' if u > 80 else 'orange' if u > 50 else 'red' 
                       for u in active_load["load_util"]]
        
        ax.barh(active_load["vehicle"], active_load["load_util"], color=colors_load)
        ax.set_xlabel("Utilización de Carga (%)", fontsize=12)
        ax.set_ylabel("Vehículo", fontsize=12)
        ax.set_title("Utilización de Capacidad de Carga por Vehículo", fontsize=14, fontweight='bold')
        ax.axvline(x=80, color='green', linestyle='--', alpha=0.5, label='Objetivo: 80%')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, axis='x')
        
        # Valores
        for idx, row in active_load.iterrows():
            ax.text(row["load_util"], row["vehicle"], f' {row["load_util"]:.1f}%', 
                    va='center', fontsize=9)
    else:
        ax.text(0.5, 0.5, 'No hay vehículos con carga', ha='center', va='center')
    
    fig.savefig(out_fig / "10_vehicle_load_util.png", bbox_inches="tight")
    plt.close(fig)
    print("10_vehicle_load_util.png")

    # ====================================================================
    # FIGURA 11: DISTANCIA VS COSTO POR VEHÍCULO
    # ====================================================================
    fig, ax = plt.subplots(figsize=(10, 6))
    
    active_dist = vehicle_kpis[vehicle_kpis["distance_km"] > 0]
    
    if not active_dist.empty:
        ax.scatter(active_dist["distance_km"], active_dist["cost"], 
                   s=100, alpha=0.6, edgecolors='black', linewidth=1.5)
        
        # Etiquetas de vehículos
        for idx, row in active_dist.iterrows():
            ax.annotate(row["vehicle"], 
                        (row["distance_km"], row["cost"]),
                        textcoords="offset points", xytext=(5, 5), fontsize=9)
        
        ax.set_xlabel("Distancia Total (km)", fontsize=12)
        ax.set_ylabel("Costo Total (COP)", fontsize=12)
        ax.set_title("Relación Distancia vs Costo por Vehículo", fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'No hay datos de distancia', ha='center', va='center')
    
    fig.savefig(out_fig / "11_distance_vs_cost.png", bbox_inches="tight")
    plt.close(fig)
    print("11_distance_vs_cost.png")

    print(f"\n {11} figuras generadas exitosamente en: {out_fig}\n")


if __name__ == "__main__":
    from pathlib import Path
    DATA_DIR = Path(__file__).resolve().parents[1]
    make_all_figures(str(DATA_DIR))