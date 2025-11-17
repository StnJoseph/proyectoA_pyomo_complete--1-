
# proyectoA_pyomo

Este paquete **cumple 100%** con el enunciado del Problema A en lo que pediste explícitamente:
- **Rango útil** (R_k), **rendimiento** (eff km/L) y **precio de combustible** (fuel_price) en la **función objetivo**.
- Costos por **tiempo** (w_time * t_ij), por **km** (c_km * d_ij) y **fijo** (f_fixed).
- Restricciones: visita única, continuidad por vehículo, salida/regreso al mismo CD, capacidad vehicular, conservación y cap. de CD, acceso urbano, límites de rango y tiempo.
- **Preprocesamiento**: `pipelines/preprocess.py` genera `arcs.csv` (dist, time) y copia `nodes_*` a `outputs/tables`.
- **Mini-caso** SIEMPRE reproducible sin solver externo: `python run_mini_case.py` genera **TODOS** los CSVs que tu .tex usa:
  - `outputs/tables/selected_arcs_detailed.csv`
  - `outputs/tables/flows_by_arc_per_vehicle.csv`
  - `outputs/tables/center_kpis.csv`
  - `outputs/tables/vehicle_kpis.csv`
  - y en `report/assets/`: `caso_a_mano_arcos.csv`, `caso_a_mano_totales.csv`
- **Full** (opcional) con Pyomo: `python pipelines/preprocess.py` y luego `python run_full.py` (requiere pyomo + solver).

## Rutas y nombres
Se mantienen **idénticos** a tu LaTeX: `proyectoA_pyomo/outputs/tables/*.csv` y `proyectoA_pyomo/report/assets/*.csv`.

## Pasos rápidos
1. (Mini-caso) `python run_mini_case.py`  → genera todos los CSVs para compilar el .tex.
2. (Completo)  `python pipelines/preprocess.py` → genera `arcs.csv` desde coordenadas.
   Luego `python run_full.py` (con solver disponible) → exporta CSVs espejo.

## Datos necesarios para el caso completo
- `inputs/nodes_centers.csv`: id, cap_c, lat, lon
- `inputs/nodes_clients.csv`: id, q, lat, lon
- `inputs/vehicles.csv`: id, Q, R, eff, w_time, c_km, f_fixed, Tmax
- `inputs/economics.csv`: fuel_price, alpha
- `inputs/access.csv`: node_id, veh_id, allowed

## Validación
El mini-caso valida pipeline y restricciones (capacidad, rango, tiempo, acceso). El completo replica el mismo modelo con Pyomo.

