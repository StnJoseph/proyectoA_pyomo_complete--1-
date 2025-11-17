
import pandas as pd
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[0])
mini_arcos = pd.read_csv(f"{ROOT}/report/assets/caso_a_mano_arcos.csv")
mini_tot = mini_arcos.groupby("veh")[["distance_km","time_h","cost"]].sum().reset_index()
mini_tot.rename(columns={"veh":"vehicle","distance_km":"total_km","time_h":"total_h","cost":"total_cost"}, inplace=True)
mini_tot.to_csv(f"{ROOT}/report/assets/caso_a_mano_totales.csv", index=False)
print("Mini-case tables regenerated.")
