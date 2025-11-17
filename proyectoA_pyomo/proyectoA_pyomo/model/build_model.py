
# model/build_model.py
# Complete Pyomo model with all parameters mentioned. This file is ready to be imported by run scripts.
from pyomo.environ import (
    ConcreteModel, Set, Param, Var, NonNegativeReals, Binary, Reals, Constraint, Objective, summation, value
)

def build_model(data):
    m = ConcreteModel()

    # Sets
    m.C = Set(initialize=data['C'])
    m.I = Set(initialize=data['I'])
    m.N = m.C | m.I
    m.K = Set(initialize=data['K'])
    m.A = Set(initialize=data['A'], dimen=2)

    # Parameters
    m.q = Param(m.I, initialize=data['q'], within=NonNegativeReals)
    m.cap_c = Param(m.C, initialize=data['cap_c'], within=NonNegativeReals)
    m.Q = Param(m.K, initialize=data['Q'], within=NonNegativeReals)
    m.Aacc = Param(m.N, m.K, initialize=data['A_access'], within=NonNegativeReals)

    m.dist = Param(m.N, m.N, initialize=data['dist'], default=0.0, within=NonNegativeReals)
    m.tt   = Param(m.N, m.N, initialize=data['time'], default=0.0, within=NonNegativeReals)

    m.fuel_price = Param(initialize=data['fuel_price'])
    m.eff = Param(m.K, initialize=data['eff_k'], within=NonNegativeReals)
    m.w_time = Param(m.K, initialize=data['w_time'], within=NonNegativeReals)
    m.c_km = Param(m.K, initialize=data['c_km'], within=NonNegativeReals)
    m.f_fixed = Param(m.K, initialize=data['f_fixed'], within=NonNegativeReals)
    m.R = Param(m.K, initialize=data['range_k'], within=NonNegativeReals, default=1e9)
    m.Tmax = Param(m.K, initialize=data['Tmax_k'], within=NonNegativeReals, default=1e9)

    # Variables
    m.x = Var(m.K, m.A, domain=Binary)                 # route selection
    m.y = Var(m.K, m.A, domain=NonNegativeReals)       # flow
    m.z = Var(m.C, m.K, domain=Binary)                 # center chosen by vehicle
    m.u = Var(m.K, domain=Binary)                      # vehicle active
    m.s = Var(m.C, domain=NonNegativeReals)            # center supply

    # Objective
    def obj_rule(m):
        arc_cost = 0
        for k in m.K:
            for (i,j) in m.A:
                fuel = m.fuel_price * m.dist[i,j] / (m.eff[k]+1e-9)
                timec = m.w_time[k] * m.tt[i,j]
                kmc = m.c_km[k] * m.dist[i,j]
                arc_cost += (fuel + timec + kmc) * m.x[k,i,j]
        fixed = sum(m.f_fixed[k]*m.u[k] for k in m.K)
        return arc_cost + fixed
    m.OBJ = Objective(rule=obj_rule)

    # Constraints
    # 1) Unique visit (in/out) per client across all vehicles
    def visit_in(m, i):
        return sum(m.x[k,i,j] for k in m.K for (ii,j) in m.A if ii==i) == 1
    def visit_out(m, i):
        return sum(m.x[k,j,i] for k in m.K for (j,ii) in m.A if ii==i) == 1
    m.VisitIn = Constraint(m.I, rule=visit_in)
    m.VisitOut = Constraint(m.I, rule=visit_out)

    # 2) Continuity per vehicle on clients
    def continuity(m, k, i):
        return sum(m.x[k,i,j] for (ii,j) in m.A if ii==i) == sum(m.x[k,j,i] for (j,ii) in m.A if ii==i)
    m.Cont = Constraint(m.K, m.I, rule=continuity)

    # 3) Start/end at same center and link with u_k
    def start_at_center(m,k,c):
        return sum(m.x[k,c,j] for (cc,j) in m.A if cc==c) == m.z[c,k]
    def end_at_center(m,k,c):
        return sum(m.x[k,i,c] for (i,cc) in m.A if cc==c) == m.z[c,k]
    def one_center_per_vehicle(m,k):
        return sum(m.z[c,k] for c in m.C) == m.u[k]
    m.Start = Constraint(m.K, m.C, rule=start_at_center)
    m.End   = Constraint(m.K, m.C, rule=end_at_center)
    m.OneCenter = Constraint(m.K, rule=one_center_per_vehicle)

    # 4) Vehicle capacity
    def cap_arc(m,k,i,j):
        return m.y[k,i,j] <= m.Q[k]*m.x[k,i,j]
    m.CapArc = Constraint(m.K, m.A, rule=cap_arc)

    # 5) Flow conservation and center capacity
    def flow_clients(m, i):
        return sum(m.y[k,j,i] for k in m.K for (j,ii) in m.A if ii==i) - \
               sum(m.y[k,i,j] for k in m.K for (ii,j) in m.A if ii==i) == m.q[i]
    m.FlowClients = Constraint(m.I, rule=flow_clients)

    def flow_center_balance(m, c, k):
        return sum(m.y[k,c,j] for (cc,j) in m.A if cc==c) - \
               sum(m.y[k,j,c] for (j,cc) in m.A if cc==c) == m.s[c]
    m.FlowCenter = Constraint(m.C, m.K, rule=flow_center_balance)

    def center_cap(m, c):
        return m.s[c] <= m.cap_c[c]
    m.CenterCap = Constraint(m.C, rule=center_cap)

    # 6) Urban access
    def access_i(m,k,i,j):
        return m.x[k,i,j] <= m.Aacc[i,k]
    def access_j(m,k,i,j):
        return m.x[k,i,j] <= m.Aacc[j,k]
    m.AccessI = Constraint(m.K, m.A, rule=access_i)
    m.AccessJ = Constraint(m.K, m.A, rule=access_j)

    # 7) Range and time duration
    def range_limit(m,k):
        return sum(m.dist[i,j]*m.x[k,i,j] for (i,j) in m.A) <= m.R[k]*m.u[k]
    def time_limit(m,k):
        return sum(m.tt[i,j]*m.x[k,i,j] for (i,j) in m.A) <= m.Tmax[k]*m.u[k]
    m.Range = Constraint(m.K, rule=range_limit)
    m.Time  = Constraint(m.K, rule=time_limit)

    return m
