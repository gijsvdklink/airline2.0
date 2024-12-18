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
        flight_no = row['#']  
        L.add(flight_no)
        CAP_i[flight_no] = row['Cap']  
    return L, CAP_i

# Function to load itinerary data
def load_itinerary_data(itineraries_df):
    P = set()
    fare_p = {}
    D_p = {}
    delta_p_i = defaultdict(lambda: defaultdict(int))
    for _, row in itineraries_df.iterrows():
        itinerary_no = row['#']
        P.add(itinerary_no)
        fare_p[itinerary_no] = row['Fare']  
        D_p[itinerary_no] = row['Demand']  
        if pd.notna(row['Leg1']):
            delta_p_i[itinerary_no][row['Leg1']] = 1
        if pd.notna(row['Leg2']):
            delta_p_i[itinerary_no][row['Leg2']] = 1
    return P, fare_p, D_p, delta_p_i

# Function to load recapture data
def load_recapture_data(recapture_df):
    b_p_r = defaultdict(lambda: defaultdict(float))
    P_from = []  # Lijst voor 'From' itineraries
    R_to = []    

    # Itereer door de recapture data
    for _, row in recapture_df.iterrows():
        itinerary_no_from = int(row['From'])  
        itinerary_no_to = int(row['To'])      
        recapture_rate = row['Rate']          
        b_p_r[itinerary_no_from][itinerary_no_to] = recapture_rate
        if itinerary_no_from not in P_from:
            P_from.append(itinerary_no_from)
        if itinerary_no_to not in R_to:
            R_to.append(itinerary_no_to)
    return b_p_r, P_from, R_to



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
b_p_r, P_from, R_to = load_recapture_data(recapture_df)


#----------------------------------------------------------------------------------------------------------------------------------------
# Function to calculate total demand per flight based on the itineraries
def compute_Qi(itineraries_df):
    flight_demand = defaultdict(lambda: {'Total Demand': 0, 'Itineraries': []})
    for _, row in itineraries_df.iterrows():
        itinerary_no = row['#']  
        demand = row['Demand']   
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


# execute to calulate total demand 
Q_i, flight_demand = compute_Qi(itineraries_df)

# Compute Q_i - CAP_i en voeg dit toe aan de final matrix
demand_data = []
for flight, info in flight_demand.items():
    total_demand = info['Total Demand']
    capacity = CAP_i.get(flight, 0)
    diff = total_demand - capacity  # Q_i - CAP_i
    itineraries = ", ".join(map(str, info['Itineraries']))
    demand_data.append([flight, total_demand, capacity, diff, itineraries])


demand_df = pd.DataFrame(demand_data, columns=['Flight No.', 'Total Demand (Q_i)', 'Capacity (CAP_i)', 'Q_i - CAP_i', 'Itineraries'])
print("\nTotal Demand per Flight with Q_i - CAP_i:")
print(demand_df.to_string(index=False))


#----------------------------------------------------------------------------------------------------------------------------------------
#GUROBI MODEL for the initial RMP model:

model = Model("PassengerMixFlow")

#create variables
ts = {}
for p in P:
    ts[p] = model.addVar(obj= fare_p[p], name = f"t_{p}^0", vtype=GRB.CONTINUOUS)
    
# Objective Function: Minimize the total Spilled cost
model.update()
model.setObjective(model.getObjective(), GRB.MINIMIZE)

# Constraint set 1: Ensure demand spill to itinerary 0 meets Q_i - CAP_i for all flights
for flight in L:
    capacity = CAP_i.get(flight, 0)
    diff = Q_i.get(flight, 0) - capacity  
    model.addConstr(quicksum(delta_p_i[p][flight] * ts[p] for p in P) >= diff,name=f"Flight_{flight}_Spill")

# Constraint set 2: t_p_r (passengers spilled) cannot exceed D_p 
for p in P:
    model.addConstr(
        ts[p] <= D_p[p],
        name=f"Demand_Limit_{p}")
    
# Constraint set 3: t_p_r must be non-negative
for p in P:
    model.addConstr(
        ts[p] >= 0,
        name=f"NonNegative_t_{p}_0")

print('------------------RMP problem----------------------------')
#execute model 
model.update()
model.optimize()
model.write("passenger_reallocation_RMP.lp")
if model.status == GRB.Status.OPTIMAL:
    print(f"\nOptimal value of the objective function: {model.ObjVal}")
else:
    print("\nOptimization was unsuccessful.")


#----------------------------------------------------------------------------------------------------------------------------------------
#Pricing problem


#function to generate Dual variables 
def calculate_dual_variables(model):
    pi = {}       
    sigma = {}    

    # Loop through all constraints in the model
    for constraint in model.getConstrs():
        name = constraint.getAttr('ConstrName')  
        dual_value = constraint.getAttr('Pi')    
        
        # Categorize dual variables based on the constraint name
        if "Flight" in name:  
            flight = int(name.split('_')[1])  
            pi[flight] = dual_value
        elif "Demand_Limit" in name: 
            itinerary = int(name.split('_')[2])  
            sigma[itinerary] = dual_value
    return pi, sigma



def compute_t_p_r_prime(P_from, R_to, fare_p, delta_p_i, pi, sigma, b_p_r):
    results = []

    for p in P_from:  
        fare_p_value = fare_p[p] 
        pi_sum_p = sum(pi[flight] for flight in delta_p_i[p] if delta_p_i[p][flight] == 1 and flight in pi)

        for r in R_to:  
            if b_p_r[p][r] > 0:  
                fare_r_value = fare_p[r]  
                pi_sum_r = sum(pi[flight] for flight in delta_p_i[r] if delta_p_i[r][flight] == 1 and flight in pi)
                sigma_p_value = sigma.get(p, 0)

                t_p_r_prime = (fare_p_value - pi_sum_p) - b_p_r[p][r] * (fare_r_value - pi_sum_r) - sigma_p_value
                results.append((p, r, t_p_r_prime))
    return results



#----------------------------------------------------------------------------------------------------------------------------------------
#functions for Creating new variables


def create_new_variables(model, results):
    new_variables = {}  # Dictionary om de nieuwe variabelen op te slaan
    negative_found = False  # Flag om te controleren of er negatieve t_p^r' zijn

    # Itereer door alle resultaten en controleer op negatieve t_p^r'
    for p, r, t_p_r_prime in results:
        if t_p_r_prime < 0:  # Controleer of t_p_r_prime negatief is
            negative_found = True  # Zet flag naar True
            var_name = f"t_{p}^{r}"  # Naam van de nieuwe variabele
            # Voeg de nieuwe variabele toe aan het model
            new_variables[(p, r)] = model.addVar(lb=0, name=var_name, vtype=GRB.CONTINUOUS)
            print(f"New decision variable created: {var_name}")

    # Controleer of er geen negatieve t_p^r' waren
    if not negative_found:
        print("No new decision variables, this is the optimal solution.")
        return new_variables  # Lege dictionary wordt teruggegeven

    # Update het model om de nieuwe variabelen toe te voegen
    model.update()
    return new_variables



#----------------------------------------------------------------------------------------------------------------------------------------
#functions for Updating the model

def update_objective_function(model, new_variables, fare_p, b_p_r):
    current_objective = model.getObjective()
    print(current_objective)

    for (p, r), var in new_variables.items():
        new_term = (fare_p[p] - b_p_r[p][r] * fare_p[r]) * var
        current_objective += new_term  

    model.setObjective(current_objective, GRB.MINIMIZE)


def update_capacity_constraints(model, L , delta_p_i, new_variables, b_p_r, P, R_to):
 
    for flight in L:
        constraint_name = f"Flight_{flight}_Spill"
        constraint = model.getConstrByName(constraint_name)

        for (p, r), var in new_variables.items():
            if delta_p_i[p][flight] == 1: 
                model.chgCoeff(constraint, var, 1)  
            if delta_p_i[r][flight] == 1:  
                model.chgCoeff(constraint, var, -b_p_r[p][r])  

    model.update()



def update_demand_constraints(model, P, R_to, new_variables, ts, D_p):
    for p in P:
        constraint_name = f"Demand_Limit_{p}"
        constraint = model.getConstrByName(constraint_name)
        
        if constraint:
            model.chgCoeff(constraint, ts[p], 1)  
            
            for r in R_to:
                if (p, r) in new_variables:
                    model.chgCoeff(constraint, new_variables[(p, r)], 1)  
        else:
            print(f"Constraint Demand_Limit_{p} not found!")

    model.update()


def add_non_negativity_constraints(model, new_variables):
    for (p, r), var in new_variables.items():
        model.addConstr(var >= 0, name=f"NonNegative_t_{p}^{r}")
    
    model.update()


#----------------------------------------------------------------------------------------------------------------------------------------

print('------------------Iteration 2----------------------------')

pi, sigma = calculate_dual_variables(model)
results = compute_t_p_r_prime(P_from, R_to, fare_p, delta_p_i, pi, sigma, b_p_r)
new_variables = create_new_variables(model, results)
update_objective_function(model, new_variables, fare_p, b_p_r)
update_capacity_constraints(model, L, delta_p_i, new_variables, b_p_r, P, R_to)
update_demand_constraints(model, P, R_to, new_variables, ts, D_p)
add_non_negativity_constraints(model, new_variables)
model.update()


# Optimaliseer het model
model.optimize()

# Controleer de status en print de objective value
if model.status == GRB.Status.OPTIMAL:
    print(f"\nOptimal value of the objective function (Iteration 2): {model.ObjVal}")
else:
    print("\nOptimization was unsuccessful in Iteration 2.")

# Export het model naar een LP-bestand voor verdere inspectie
model.write("passenger_reallocation_iteration2.lp")

# Print alle decision variabelen na optimalisatie
print("\nOptimized Decision Variables (Iteration 2):")
for v in model.getVars():
    print(f"{v.VarName}: {v.X}")

pi2, sigma2 = calculate_dual_variables(model)
results2 = compute_t_p_r_prime(P_from, R_to, fare_p, delta_p_i, pi2, sigma2, b_p_r)


new_variables = create_new_variables(model, results2)



