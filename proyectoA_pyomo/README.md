
# proyectoA_pyomo

Pipeline completo para el **Problema A (urbano)**: preprocesamiento, modelo MILP (Pyomo),
exportación de tablas espejo y generación de figuras para el documento LaTeX.

## Requisitos (local)
- Python 3.9+
- `pip install pyomo pandas numpy matplotlib`
- Instalar un solver MILP (al menos uno):
  - Recomendado: HiGHS (`pip install highspy`)
  - Alternativas: CBC, GLPK (según SO)

## Estructura
```
proyectoA_pyomo/
  data/raw/                 # nodos (CD, clientes) y demandas
  data/params/              # params de vehículos, acceso, costos
  model/                    # Pyomo
  preprocess/               # preprocesamiento y construcción de arcs_cache
  reporting/                # gráficos y mini-caso
  outputs/figures/          # se generan
  outputs/tables/           # se generan
  main.py                   # orquestador de todo
  README.md
```

## Ejecución (desde la carpeta que contiene `proyectoA_pyomo/`)
```bash
python proyectoA_pyomo/main.py
# o
python -m proyectoA_pyomo.main
```

Al finalizar, revisa:
- `outputs/tables/selected_arcs_detailed.csv`, `flows_by_arc_per_vehicle.csv`, `center_kpis.csv`, `vehicle_kpis.csv`
- `outputs/figures/*.png`
- `report/assets/caso_a_mano_*.csv` y `caso_a_mano_prehecho.png`
```

