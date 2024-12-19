import pandas as pd
from collections import defaultdict
from gurobipy import *

# Path to the Excel file
file_path = './data/Group_16.xlsx'

# Load Excel file
excel_data = pd.ExcelFile(file_path)

#----------------------------------------------------------------------------------------------------------------------------------------
# Function to load sheet 1 of excel file 
def load_flight_data(flights_df):
    L = set()                     
    CAP_i = {}
    for _, row in flights_df.iterrows():
        L.add(row['Flight No.'])
        CAP_i[row['Flight No.']] = row['Capacity']
    return L, CAP_i

# Function to load sheet 2 of excel file 
def load_itinerary_data(itineraries_df):
    P = set()
    fare_p = {}
    D_p = {}
    delta_p_i = defaultdict(lambda: defaultdict(int))
    for _, row in itineraries_df.iterrows():
        itinerary_no = row['Itinerary']
        P.add(itinerary_no)
        fare_p[itinerary_no] = row['Price [EUR]']
        D_p[itinerary_no] = row['Demand']
        if pd.notna(row['Flight 1']):
            delta_p_i[itinerary_no][row['Flight 1']] = 1
        if pd.notna(row['Flight 2']):
            delta_p_i[itinerary_no][row['Flight 2']] = 1
    return P, fare_p, D_p, delta_p_i

# Function to load sheet 3 of excel file 
def load_recapture_data(recapture_df):
    b_p_r = defaultdict(lambda: defaultdict(float))
    P_from = []  # Lijst voor 'From' itineraries
    R_to = []    

    # Itereer door de recapture data
    for _, row in recapture_df.iterrows():
        itinerary_no_from = int(row['From Itinerary'])  
        itinerary_no_to = int(row['To Itinerary'])      
        recapture_rate = row['Recapture Rate']          
        b_p_r[itinerary_no_from][itinerary_no_to] = recapture_rate
        if itinerary_no_from not in P_from:
            P_from.append(itinerary_no_from)
        if itinerary_no_to not in R_to:
            R_to.append(itinerary_no_to)
    return b_p_r, P_from, R_to

#Function to calculate the total demand per fligt, by going over all itineraries
def compute_Qi(itineraries_df):
    flight_demand = defaultdict(lambda: {'Total Demand': 0, 'Itineraries': []})
    for _, row in itineraries_df.iterrows():
        itinerary_no = row['Itinerary']
        flight1 = row['Flight 1']
        flight2 = row['Flight 2']
        demand = row['Demand']
        if pd.notna(flight1):
            flight_demand[flight1]['Total Demand'] += demand
            flight_demand[flight1]['Itineraries'].append(itinerary_no)
        if pd.notna(flight2):
            flight_demand[flight2]['Total Demand'] += demand
            flight_demand[flight2]['Itineraries'].append(itinerary_no)
    Q_i = {flight: info['Total Demand'] for flight, info in flight_demand.items()}
    return Q_i, flight_demand


#----------------------------------------------------------------------------------------------------------------------------------------
#Execute functions to load Data

# Load Data
flights_df = excel_data.parse('Flights')
itineraries_df = excel_data.parse('Itineraries')
recapture_df = excel_data.parse('Recapture')

L, CAP_i = load_flight_data(flights_df)
P, fare_p, D_p, delta_p_i = load_itinerary_data(itineraries_df)
Q_i, flight_demand = compute_Qi(itineraries_df)
b_p_r, P_from, R_to = load_recapture_data(recapture_df)


#----------------------------------------------------------------------------------------------------------------------------------------

# Compute Q_i - CAP_i and Add to the Final Matrix
demand_data = []
for flight, info in flight_demand.items():
    total_demand = info['Total Demand']
    capacity = CAP_i.get(flight, 0)
    diff = total_demand - capacity  # Q_i - CAP_i
    itineraries = ", ".join(map(str, info['Itineraries']))
    demand_data.append([flight, total_demand, capacity, diff, itineraries])

# Final DataFrame
demand_df = pd.DataFrame(demand_data, columns=['Flight No.', 'Total Demand (Q_i)', 'Capacity (CAP_i)', 'Q_i - CAP_i', 'Itineraries'])
print("\nTotal Demand per Flight with Q_i - CAP_i:")
print(demand_df.to_string(index=False))


#----------------------------------------------------------------------------------------------------------------------------------------
#GUROBI MODEL


# Gurobi Model: Optimization
model = Model("PassengerMixflow")

# Decision Variables: t_p^0 -> Passengers moved from itinerary p to fictitious itinerary
t_p_0 = model.addVars(P, name="t_p^0", vtype=GRB.CONTINUOUS)

    
# Constraint set 1: Ensure demand spill to itinerary 0 meets Q_i - CAP_i for all flights
for flight in L:
    capacity = CAP_i.get(flight, 0)
    diff = Q_i.get(flight, 0) - capacity  # Q_i - CAP_i

    model.addConstr(
        quicksum(delta_p_i[p][flight] * t_p_0[p] for p in P) >= diff,
        name=f"Flight_{flight}_Spill"
    )

# Constraint set 2: t_p_0 (passengers spilled) cannot exceed D_p (total demand for itinerary p)
for p in P:
    model.addConstr(
        t_p_0[p] <= D_p[p],
        name=f"Demand_Limit_{p}")
    
# Constraint set 3: t_p_0 must be non-negative
for p in P:
    model.addConstr(
        t_p_0[p] >= 0,
        name=f"NonNegative_t_{p}_0")


# Objective Function: Minimize the total Spilled cost
model.setObjective(quicksum(fare_p[p] * t_p_0[p] for p in P if p in fare_p), GRB.MINIMIZE)

model.update()

# Solve Model
model.optimize()

# Export Model to LP File
model.write("passenger_mixflow_model_new.lp")
model.write("passenger_mixflow_model_new.mps")

# Print Objective Function Value
if model.status == GRB.Status.OPTIMAL:
    print(f"\nOptimal value of the objective function: {model.ObjVal}")
else:
    print("\nOptimization was unsuccessful.")


# # Print Decision Variables
# print("\nDecision Variables:")
# for v in model.getVars():
#     print(f"{v.VarName}: {v.X}")


# print("\nDual Variables (Shadow Prices):")
# for constraint in model.getConstrs():
#     print(f"{constraint.ConstrName}: Dual = {constraint.Pi}")

#----------------------------------------------------------------------------------------------------------------------------------------
#Pricing Model

def calculate_dual_variables(model):
    pi = {}       # Dual variables for capacity constraints (Pi)
    sigma = {}    # Dual variables for demand constraints (Sigma)

    # Loop through all constraints in the model
    for constraint in model.getConstrs():
        name = constraint.getAttr('ConstrName')  # Name of the constraint
        dual_value = constraint.getAttr('Pi')    # Dual value of the constraint
        
        # Categorize dual variables based on the constraint name
        if "Flight" in name:  # Capacity constraints
            flight = name.split('_')[1]  # Extract flight identifier (keep as string)
            pi[flight] = dual_value
        elif "Demand_Limit" in name:  # Demand constraints
            itinerary = name.split('_')[2]  # Extract itinerary identifier (keep as string)
            sigma[itinerary] = dual_value

    # Optional: Print the dual variables
    print("\nDual Variables for Capacity Constraints (Pi):")
    for flight, value in pi.items():
        print(f"Flight {flight}: {value}")

    print("\nDual Variables for Demand Constraints (Sigma):")
    for itinerary, value in sigma.items():
        print(f"Itinerary {itinerary}: {value}")

    return pi, sigma


# Retrieve dual variables using the new function
pi, sigma = calculate_dual_variables(model)

def compute_t_p_r_prime(P_from, R_to, fare_p, delta_p_i, pi, sigma, b_p_r):
    results = []

    for p in P_from:  # Itereer alleen over P_from
        fare_p_value = fare_p[p]  # Fare van itinerary p
        # Som van pi alleen voor de vluchten waar delta_p_i[p][flight] == 1
        pi_sum_p = sum(pi[flight] for flight in delta_p_i[p] if delta_p_i[p][flight] == 1 and flight in pi)

        for r in R_to:  # Itereer alleen over R_to
            if b_p_r[p][r] > 0:  # Alleen als recapture rate > 0
                fare_r_value = fare_p[r]  # Fare van itinerary r
                # Som van pi alleen voor de vluchten waar delta_p_i[r][flight] == 1
                pi_sum_r = sum(pi[flight] for flight in delta_p_i[r] if delta_p_i[r][flight] == 1 and flight in pi)
                sigma_p_value = sigma.get(p, 0)

                # Bereken t_p^{r'}
                t_p_r_prime = (fare_p_value - pi_sum_p) - b_p_r[p][r] * (fare_r_value - pi_sum_r) - sigma_p_value
                results.append((p, r, t_p_r_prime))

                # # Debugging: print tussenwaarden
                # print(f"\nItinerary {p} to {r}:")
                # print(f"Fare_p: {fare_p_value}, Sum Pi_p: {pi_sum_p}")
                # print(f"Recapture rate b_p_r: {b_p_r[p][r]}")
                # print(f"Fare_r: {fare_r_value}, Sum Pi_r: {pi_sum_r}")
                # print(f"Sigma_p: {sigma_p_value}")
                # print(f"Computed t_p^r: {t_p_r_prime}")

    return results

results = compute_t_p_r_prime(P_from, R_to, fare_p, delta_p_i, pi, sigma, b_p_r)


print("\nComputed t_p^{r'} Values:")
for p, r, t_p_r_prime in results:
    if t_p_r_prime < 0:
        print(f"t_{p}^{r}: {t_p_r_prime}")
