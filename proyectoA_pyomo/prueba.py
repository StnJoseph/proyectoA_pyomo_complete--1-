import pandas as pd
kpis = pd.read_csv("outputs/tables/vehicle_kpis.csv")
print(kpis[["vehicle", "time_h"]])