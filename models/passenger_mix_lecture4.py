import pandas as pd
from collections import defaultdict
from gurobipy import *

# Path to the Excel file
file_path = './data/AE4423_PMF_Exercise_Input.xlsx'

# Load Excel file
excel_data = pd.ExcelFile(file_path)

#----------------------------------------------------------------------------------------------------------------------------------------
# Function to load sheet 1 of excel file 


def load_flight_data(flights_df):
    L = set()
    CAP_i = {}
    for _, row in flights_df.iterrows():
        flight_no = row['#']  # Vluchtnummer
        L.add(flight_no)
        CAP_i[flight_no] = row['Cap']  # Capaciteit
    return L, CAP_i

# Functie om Itineraries data te laden
def load_itinerary_data(itineraries_df):
    P = set()
    fare_p = {}
    D_p = {}
    delta_p_i = defaultdict(lambda: defaultdict(int))
    for _, row in itineraries_df.iterrows():
        itinerary_no = row['#']
        P.add(itinerary_no)
        fare_p[itinerary_no] = row['Fare']  # Prijs
        D_p[itinerary_no] = row['Demand']  # Vraag
        if pd.notna(row['Leg1']):
            delta_p_i[itinerary_no][row['Leg1']] = 1
        if pd.notna(row['Leg2']):
            delta_p_i[itinerary_no][row['Leg2']] = 1
    return P, fare_p, D_p, delta_p_i

# Functie om Recapture data te laden
def load_recapture_data(recapture_df):
    b_p_r = defaultdict(lambda: defaultdict(float))
    for _, row in recapture_df.iterrows():
        p = row['From']  # Itinerary From
        r = row['To']    # Itinerary To
        recapture_rate = row['Rate']  # Recapture Rate
        b_p_r[p][r] = recapture_rate
    return b_p_r


#----------------------------------------------------------------------------------------------------------------------------------------
#Execute functions to load Data


# Load Flights Data
flights_df = excel_data.parse('Flights')
L, CAP_i = load_flight_data(flights_df)

# Load Itineraries Data
itineraries_df = excel_data.parse('Itineraries')
P, fare_p, D_p, delta_p_i = load_itinerary_data(itineraries_df)

# Load Recapture Data
recapture_df = excel_data.parse('Recapture')
b_p_r = load_recapture_data(recapture_df)


#----------------------------------------------------------------------------------------------------------------------------------------
# Functie om totale vraag per vlucht (Q_i) en flight_demand te berekenen
def compute_Qi(itineraries_df):
    flight_demand = defaultdict(lambda: {'Total Demand': 0, 'Itineraries': []})
    for _, row in itineraries_df.iterrows():
        itinerary_no = row['#']  # Itinerary nummer
        demand = row['Demand']   # Vraag per itinerary
        flight1 = row['Leg1']
        flight2 = row['Leg2']
        
        if pd.notna(flight1):
            flight_demand[flight1]['Total Demand'] += demand
            flight_demand[flight1]['Itineraries'].append(itinerary_no)
        if pd.notna(flight2):
            flight_demand[flight2]['Total Demand'] += demand
            flight_demand[flight2]['Itineraries'].append(itinerary_no)
    
    Q_i = {flight: info['Total Demand'] for flight, info in flight_demand.items()}
    return Q_i, flight_demand


# Bereken Q_i en flight_demand
Q_i, flight_demand = compute_Qi(itineraries_df)

# Compute Q_i - CAP_i en voeg dit toe aan de final matrix
demand_data = []
for flight, info in flight_demand.items():
    total_demand = info['Total Demand']
    capacity = CAP_i.get(flight, 0)
    diff = total_demand - capacity  # Q_i - CAP_i
    itineraries = ", ".join(map(str, info['Itineraries']))
    demand_data.append([flight, total_demand, capacity, diff, itineraries])

# Maak de DataFrame
demand_df = pd.DataFrame(demand_data, columns=['Flight No.', 'Total Demand (Q_i)', 'Capacity (CAP_i)', 'Q_i - CAP_i', 'Itineraries'])
print("\nTotal Demand per Flight with Q_i - CAP_i:")
print(demand_df.to_string(index=False))


#----------------------------------------------------------------------------------------------------------------------------------------
#GUROBI MODEL


# Gurobi Model: Optimization
model = Model("PassengerReallocation")

# Decision Variables: t_p^0 -> Passengers moved from itinerary p to fictitious itinerary
# t_p_0 = model.addVars(P, vtype=GRB.CONTINUOUS)
ts = {}

for p in P:
    ts[p] = model.addVar(obj= fare_p[p], name = f"t_{p}^0", lb = 0, vtype=GRB.CONTINUOUS)
    
# Objective Function: Minimize the total Spilled cost
model.update()
model.setObjective(model.getObjective(), GRB.MINIMIZE)

# Constraint set 1: Ensure demand spill to itinerary 0 meets Q_i - CAP_i for all flights
for flight in L:
    capacity = CAP_i.get(flight, 0)
    diff = Q_i.get(flight, 0) - capacity  # Q_i - CAP_i

    model.addConstr(
        quicksum(delta_p_i[p][flight] * ts[p] for p in P) >= diff,
        name=f"Flight_{flight}_Spill"
    )

# Constraint set 2: t_p_0 (passengers spilled) cannot exceed D_p (total demand for itinerary p)
for p in P:
    model.addConstr(
        ts[p] <= D_p[p],
        name=f"Demand_Limit_{p}")
    
# # Constraint set 3: t_p_0 must be non-negative
# for p in P:
#     model.addConstr(
#         t_p_0[p] >= 0,
#         name=f"NonNegative_t_{p}_0")



model.update()

# Solve Model
model.optimize()

# Export Model to LP File
model.write("passenger_reallocation_model_lecture_example_new.lp")
model.write("passenger_reallocation_model_lecture_example_new.mps")

# Print Objective Function Value
if model.status == GRB.Status.OPTIMAL:
    print(f"\nOptimal value of the objective function: {model.ObjVal}")
else:
    print("\nOptimization was unsuccessful.")

# Print Decision Variables
print("\nDecision Variables:")
for v in model.getVars():
    print(f"{v.VarName}: {v.X}")

print('---------------------------ITERATION 2-------------------------------------')

# Dual Variables ophalen
dual_vars = {c.ConstrName: c.Pi for c in model.getConstrs()}


print("\nDual Variables (Shadow Prices):")
for c_name, dual_value in dual_vars.items():
    print(f"{c_name}: {dual_value}")

# Functie om de som van de duale variabelen (shadow prices) per itinerary te berekenen
def compute_dual_sums(P, itineraries_df, dual_vars):
    dual_sums = {}
    for _, row in itineraries_df.iterrows():
        p = row['#']  # Itinerary nummer
        dual_sum = 0
        # Haal dual variables op voor Leg1 en Leg2, indien ze bestaan
        if pd.notna(row['Leg1']):
            flight1 = row['Leg1']
            dual_sum += dual_vars.get(f"Flight_{flight1}_Spill", 0)
        if pd.notna(row['Leg2']):
            flight2 = row['Leg2']
            dual_sum += dual_vars.get(f"Flight_{flight2}_Spill", 0)
        dual_sums[p] = dual_sum
    return dual_sums

# Functie om c_p^r' te berekenen
def compute_cp_r_prime(P, fare_p, b_p_r, dual_sums):
    cp_r_prime = defaultdict(lambda: defaultdict(float))
    for p in P:
        for r in P:
            b_pr = b_p_r[p].get(r, 0)  # Recapture rate
            cp_r_prime[p][r] = (fare_p[p] - dual_sums[p]) - b_pr * (fare_p[r] - dual_sums[r]) 
    return cp_r_prime

# Berekeningen
dual_sums = compute_dual_sums(P, itineraries_df, dual_vars)
cp_r_prime = compute_cp_r_prime(P, fare_p, b_p_r, dual_sums)

# Filter c_p^r' waar de waarde negatief is
negative_cp_r_prime = []
for p in P:
    for r in P:
        if b_p_r[p].get(r, 0) > 0 and cp_r_prime[p][r] < 0:  # Alleen negatieve waarden en geldige recapture rates
            negative_cp_r_prime.append((p, r, cp_r_prime[p][r]))

# How only negative values for c_p^r
print("\nNegatieve c_p^r' waarden (gefilterd):")
for p, r, value in negative_cp_r_prime:
    print(f"c_{p}^{r} = {value:.2f}")








