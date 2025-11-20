from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

centers = pd.read_csv(ROOT / "inputs" / "nodes_centers.csv")
clients = pd.read_csv(ROOT / "inputs" / "nodes_clients.csv")
center_kpis = pd.read_csv(ROOT / "outputs" / "tables" / "center_kpis.csv")

demand_total = clients["demand"].sum()
supply_total = center_kpis["supply"].sum()

print("\n========== CHEQUEO SUPPLY ==========\n")
print("Demanda total:", demand_total)
print("Suma total s[c] (desde center_kpis):", supply_total)
print("¿Suma s[c] == demanda total?:",
      abs(supply_total - demand_total) < 1e-6)

print("\nCentro | supply (s[c]) | cap | violación cap?")
print("----------------------------------------------")
cap_map = centers.set_index("id")["capacity"].to_dict()

for _, row in center_kpis.iterrows():
    c = str(row["center"])
    s = float(row["supply"])
    cap = float(cap_map[c])
    violated = s > cap + 1e-6
    print(f"{c:6s} | {s:13.4f} | {cap:3.1f} | {'SI' if violated else 'NO'}")

print()
