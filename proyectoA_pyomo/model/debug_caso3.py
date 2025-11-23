from pathlib import Path
import pandas as pd
from pyomo.environ import SolverFactory, TerminationCondition, SolverStatus
from build_model import build_model

DATA_DIR = Path(__file__).resolve().parents[1]

TIME_LIMIT = 600  # puedes subirlo a 1200 si quieres

def solve_variant(label, deactivate=None):
    """
    Construye el modelo, desactiva algunas restricciones (por nombre)
    y resuelve. Imprime si encontró solución factible o no.
    """
    print("\n" + "="*60)
    print(f"Escenario: {label}")
    print("="*60)

    m = build_model(DATA_DIR)

    # Desactivar restricciones si aplica
    if deactivate:
        for cname in deactivate:
            if hasattr(m, cname):
                getattr(m, cname).deactivate()
                print(f"  -> Restricción desactivada: {cname}")
            else:
                print(f"  (Aviso) El modelo no tiene restricción llamada {cname}")

    # Escoger solver
    for s in ["highs", "cbc", "glpk"]:
        opt = SolverFactory(s)
        if opt.available(exception_flag=False):
            solver_name = s
            break
    else:
        print("No hay solver disponible.")
        return

    opt.options = {}
    if solver_name == "highs":
        opt.options["time_limit"] = TIME_LIMIT
    elif solver_name == "cbc":
        opt.options["seconds"] = TIME_LIMIT
    elif solver_name == "glpk":
        opt.options["tmlim"] = TIME_LIMIT

    print(f"Usando solver: {solver_name} con límite {TIME_LIMIT} s")

    results = opt.solve(m, tee=True)

    status = results.solver.status
    term   = results.solver.termination_condition

    print(f"Status: {status}")
    print(f"Termination: {term}")

    if term in (TerminationCondition.optimal, TerminationCondition.feasible):
        print("→ ¡Hay solución factible/óptima!")
        return m, results

    if term == TerminationCondition.maxTimeLimit and \
       status in (SolverStatus.ok, SolverStatus.aborted):
        # Aunque no haya incumbente, dejamos registro
        print("→ Límite de tiempo alcanzado, revisar si hubo incumbente en el log.")
        return m, results

    print("→ No se encontró solución factible en este escenario.")
    return None, results


if __name__ == "__main__":
    # Escenario 0: TODO activo (el que ya sabes que falla)
    solve_variant("Caso3 - modelo completo", deactivate=[])

    # Escenario 1: sin capacidad de centros (CenterCap + SupplyCover)
    solve_variant(
        "Caso3 - sin capacidad de centros",
        deactivate=["CenterCap", "SupplyCover"]
    )

    # Escenario 2: sin restricciones de acceso urbano
    solve_variant(
        "Caso3 - sin AccessI/AccessJ",
        deactivate=["AccessI", "AccessJ"]
    )

    # Escenario 3: sin rango ni jornada
    solve_variant(
        "Caso3 - sin rango ni jornada",
        deactivate=["RangeLimit", "WorkTime"]
    )

    # Escenario 4: sin nada de lo anterior (solo CVRP clásico multi-centro)
    solve_variant(
        "Caso3 - sin centros, ni acceso, ni rango, ni jornada",
        deactivate=["CenterCap", "SupplyCover", "AccessI", "AccessJ",
                    "RangeLimit", "WorkTime"]
    )
