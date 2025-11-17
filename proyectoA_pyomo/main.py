
# -*- coding: utf-8 -*-
from pathlib import Path
from preprocess.build_data import build_data
from reporting.solve_and_export import solve_and_export
from reporting.make_figures import make_all_figures
from reporting.make_mini_case import make_mini_case

def main():
    data_dir = Path(__file__).resolve().parent
    print("[1/4] Preprocesamiento...")
    build_data(str(data_dir))
    print("[2/4] MILP (Pyomo)...")
    solve_and_export(str(data_dir))
    print("[3/4] Figuras...")
    make_all_figures(str(data_dir))
    print("[4/4] Mini–caso...")
    make_mini_case(str(data_dir))
    print("Listo. Revisa outputs/ y report/assets/.")

if __name__ == "__main__":
    main()
