# Proyecto A Caso 3 - Urban Logistics (Bogotá) - Advanced Realistic Scale

## Project Context

**LogistiCo Urban Logistics Division** - This is the **advanced realistic case** for competitive bonus eligibility. Same urban logistics context as Caso 2, but at realistic operational scale:

- **50-100 clients** across Bogotá metropolitan area
- **Multiple distribution centers** with limited inventory
- **Zone-based vehicle restrictions** (certain clients restrict truck types)
- **Realistic delivery density** and urban congestion patterns

**Case Level**: Advanced realistic (20% of implementation grade + eligible for 20% competitive bonus)

**Bonus Eligibility**: Solutions demonstrating exceptional efficiency, innovation, or business insights can earn up to 20% additional points.

## Data Files

Same structure as Caso 2 - see Project A Caso 2 README for detailed column descriptions.
With the addition of:
`clients.csv` now has the following additional column:
| Column | Type | Unit | Description |
|--------|------|------|-------------|
| VehicleSizeRestriction | String | - | Maximum vehicle type allowed (e.g., "small van", "medium van", "light truck") |

Files: `clients.csv` (50-100 rows), `vehicles.csv`, `depots.csv`

All files include **StandardizedID** columns for verification file consistency.

## Cost Parameters

**Identical to Caso 2** - see `parameters_urban.csv`:

- C_fixed: 50,000 COP/vehicle
- C_dist: 2,500 COP/km
- C_time: 7,600 COP/hour
- fuel_price: 16,300 COP/gallon
- Fuel efficiency ranges by vehicle type (22-45 km/gal)

## Caso 3 Specific Requirements

###1. **Scalability Analysis**
Document trade-offs made for larger problem size:

- Formulation modifications from Caso 2
- Solver performance (time, memory, gap)
- Why MIP/LP solvers may struggle at this scale
- Recommendations for even larger instances

### 2. **Sensitivity Analysis** (Required)

Analyze impact of ±20% changes in:

- Fuel prices
- Depot capacities
- Client demands

### 3. **Detailed Reporting**

**Per-depot statistics**:

- Inventory utilization (%)
- Number of vehicles dispatched
- Total distance/time/cost

**Per-vehicle statistics**:

- Route distance and time
- Load factor (actual load / capacity)
- Fuel consumption
- Cost breakdown

**Global statistics**:

- Average and std dev for distance, time, load
- Fleet utilization rate
- Cost per kg delivered

### 4. **Business Insights** (Critical for Bonus)

Answer strategic questions:

- Which parameters most impact total costs?
- Where are the operational bottlenecks?
- What improvements would you recommend to LogistiCo?
- How do depot locations affect route efficiency?

## Verification File Format

Same as Caso 2 - `verificacion_caso3.csv`:

```csv
VehicleId,DepotId,InitialLoad,RouteSequence,ClientsServed,DemandsSatisfied,TotalDistance,TotalTime,FuelCost
V001,CD01,750,CD01-C005-C023-C017-...-CD01,15,215-320-...,128.4,367.2,498500
```

Note: Routes will be longer with more clients per vehicle.

## Competitive Bonus Criteria (Up to +20%)

Your Caso 3 solution is evaluated relative to peers working on Project A:

1. **Cost Efficiency (7%)**:
   Total cost 15%+ below project average

2. **Computational Performance (5%)**:
   Faster solve time while maintaining quality

3. **Innovation (5%)**:
   Novel formulations, preprocessing, or solution strategies

4. **Business Analysis Depth (3%)**:
   Exceptional insights beyond requirements

**Documentation is essential** - explain your innovations and strategies!

## Visualization Requirements

**Required**:

- Interactive Folium map with all 50-100 clients and routes
- Depot utilization charts
- Cost breakdown by component

**Recommended for Bonus**:

- Route load evolution diagrams
- Sensitivity analysis charts
- Comparative analysis (before/after optimization)

## Important Notes for Caso 3

- **Scalability is key**: Focus on solving efficiently
- **Analysis depth matters**: Generic observations won't earn bonus points
- **Document everything**: Your approach, trade-offs, insights
- **Compare with Caso 2**: Show what changed and why
- Missing verification file = automatic disqualification from bonus

## Deliverables Checklist

- [ ] Modular Pyomo code with clear documentation
- [ ] verification_caso3.csv with all routes
- [ ] Sensitivity analysis results (3 parameters minimum)
- [ ] Detailed statistical reports (depot, vehicle, global levels)
- [ ] Professional visualizations (maps + charts)
- [ ] Business insights document answering strategic questions
- [ ] Scalability analysis (formulation changes, solver performance)

## Strategy Tips

1. **Start simple**: Get Caso 2 working perfectly first
2. **Incremental testing**: Test with 20, 40, 60, then full clients
3. **Monitor solver**: Track solve time and optimality gap
4. **Consider heuristics**: If MIP takes too long, document why
5. **Focus on insights**: Raw numbers aren't enough - interpret them

## ID Standardization

Same as all cases - use StandardizedID format in verification files:

- Clients: C001, C002, ..., C100
- Vehicles: V001, V002, V003, ...
- Depots: CD01, CD02, CD03
