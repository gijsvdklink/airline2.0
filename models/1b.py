#group 16 #5389283

import pandas as pd
from gurobipy import Model, GRB, quicksum


demand_data = pd.read_excel('Future_Demand_2025.xlsx', index_col=0)
distance_data = pd.read_csv('distance_matrix_with_city_names.csv', index_col=0)
data_file_path = 'data/DemandGroup16.xlsx'

airport_data = pd.read_excel(data_file_path, sheet_name='airport_data', header=None, usecols=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21])  # Include the desired columns
print (airport_data)

aircraft_data = pd.DataFrame({
    'Type': ['Aircraft 1', 'Aircraft 2', 'Aircraft 3', 'Aircraft 4'],
    'Speed': [550, 820, 850, 870],  # Speed in km/h
    'Seats': [45, 70, 150, 320],
    'TAT': [25, 35, 45, 60],  # Average Turn-Around Time in minutes
    'Max_Range': [1500, 3300, 6300, 12000],  # Maximum range in km
    'RQ': [1400, 1600, 1800, 2600],  # Runway required in meters
    'Lease_Cost': [15000, 34000, 80000, 190000],  # Weekly lease cost in EUR
    'Fixed_Cost': [300, 600, 1250, 2000],  # Fixed operating cost in EUR
    'Time_Cost': [750, 775, 1400, 2800],  # Time cost parameter in EUR/hr
    'Fuel_Cost': [1.0, 2.0, 3.75, 9.0],  # Fuel cost parameter
    'LF': [0.75, 0.75, 0.75, 0.75],  # Load Factor
    'BT': [70, 70, 70, 70]  # Maximum weekly operational hours
}, columns=['Type', 'Speed', 'Seats', 'TAT', 'Max_Range', 'RQ', 
            'Lease_Cost', 'Fixed_Cost', 'Time_Cost', 'Fuel_Cost', 'LF', 'BT'])

print(demand_data)
print(distance_data)
print(aircraft_data)

airports = list(demand_data.index)  
aircraft_types = list(aircraft_data['Type']) 

hub_airport = 'EDDF'  
g = {airport: 0 if airport == hub_airport else 1 for airport in airports}

print("Hub binary parameter (g):", g)


distance_matrix = distance_data.to_dict()  
demand_matrix = demand_data.to_dict()  

print("Airports (N):", airports)
print("Aircraft Types (K):", aircraft_types)
print("Distance from EGLL to EHAM:", distance_matrix['EHAM']['EGLL'])
print("Weekly demand from EGLL to EHAM:", demand_matrix['EHAM']['EGLL'])


aircraft_properties = {
    row['Type']: {
        'Speed': row['Speed'],                
        'Seats': row['Seats'],                
        'TAT': row['TAT'],                   
        'Max_Range': row['Max_Range'],       
        'Runway Requirement': row['RQ'],    
        'Lease_Cost': row['Lease_Cost'],      
        'Fixed_Cost': row['Fixed_Cost'],      
        'Time_Cost': row['Time_Cost'],       
        'Fuel_Cost': row['Fuel_Cost'],        
        'LF': row['LF'],                     
        'BT': row['BT']                       
    }
    for _, row in aircraft_data.iterrows()
}



print("Aircraft Properties:", aircraft_properties)


airport_data.columns = airport_data.iloc[1]  
airport_data = airport_data.drop([0, 1], axis=0)  
airport_data = airport_data.drop(columns=['ICAO Code'])
runway_lengths = airport_data.loc[4].to_dict()  
available_slots = airport_data.loc[5].to_dict()  
runway_lengths = {key: value for key, value in runway_lengths.items() if pd.notna(value)}
available_slots = {key: value for key, value in available_slots.items() if pd.notna(value)}


print("Runway Lengths:", runway_lengths)
print("Available Slots:", available_slots)


# start modelling in GUROB
model = Model('Fleet_and_Network_Planning')  


#these are the decision variables

x = model.addVars(airports, airports, name="x_ij", lb=0, vtype=GRB.INTEGER)
z = model.addVars(aircraft_types, airports, airports, name="z_kij", lb=0, vtype=GRB.INTEGER)  
w = model.addVars(airports, airports, name="w_ij", lb=0, vtype=GRB.INTEGER) 
AC = model.addVars(aircraft_types, name="AC_k", lb=0, vtype=GRB.INTEGER)  
y = model.addVars(aircraft_types, airports, vtype=GRB.BINARY, name="y_ki")
y_feas = model.addVars(aircraft_types, airports, airports, vtype=GRB.BINARY, name="y_feas_kij")


print("Decision Variables defined:")
print("x_ij[i,j]: Direct flow of passengers on route i → j (integer)")
print("z_kij[k,i,j]: Weekly flights operated by aircraft type k from i to j (integer)")
print("w_ij[i,j]: Transfer passenger flow (integer)")
print("AC_k[k]: Number of aircraft of type k leased (integer)")

# Calculate yields for each route
def calculate_yield(distance):
    return 5.9 * (distance ** -0.76) + 0.043


yields = {
    (i, j): calculate_yield(distance_matrix[j][i]) for i in airports for j in airports if i != j
}

def calculate_cost(fixed_cost, time_cost, fuel_cost, speed, distance, i, j, g, fuel_price=1.42):
    base_cost = fixed_cost + (time_cost * distance / speed) + (fuel_cost * fuel_price * distance / 1.5)
    if (1 - g[i]) + (1 - g[j]) > 0:  
        return 0.7 * base_cost
    else:
        return base_cost


flight_costs = {
    (k, i, j): calculate_cost(
        aircraft_properties[k]['Fixed_Cost'],
        aircraft_properties[k]['Time_Cost'],
        aircraft_properties[k]['Fuel_Cost'],
        aircraft_properties[k]['Speed'],
        distance_matrix[j][i],  
        i,  
        j,  
        g   
    )
    for k in aircraft_types for i in airports for j in airports if i != j
}



profit_revenue = quicksum(yields[i, j] * distance_matrix[j][i] * (x[i, j] + w[i, j]) for i in airports for j in airports if i != j)

cost_flight = quicksum(z[k, i, j] * flight_costs[k, i, j] for k in aircraft_types for i in airports for j in airports if i != j)

cost_leasing = quicksum(AC[k] * aircraft_properties[k]['Lease_Cost'] for k in aircraft_types)

#OBJECTIVE function
model.setObjective(profit_revenue - cost_flight - cost_leasing, GRB.MAXIMIZE)


print("Objective function added successfully.")

# Weekly Demand(C1)
for i in airports:
    for j in airports:
        if i != j:  
            model.addConstr(x[i, j] + w[i, j] <= demand_matrix[j][i], name=f"Demand_{i}_{j}")

# Print confirmation
print("Weekly demand (C1) added successfully.")


# (C1*) Transfer Passenger
for i in airports:
    for j in airports:
        if i != j:  
            model.addConstr(w[i, j] <= demand_matrix[j][i] * g[i] * g[j], name=f"TransferPassenger_{i}_{j}")


# Print confirmation
print("Transfer Passenger Constraints (C1*) added successfully with HUB = EDDF.")

# Weekly Capacity Constraint (C2)
for i in airports:
    for j in airports:
        if i != j:  # Exclude same airport pairs
            model.addConstr(x[i, j] +  quicksum(w[i, m] * (1 - g[j]) for m in airports if m != i) +  quicksum(w[m, i] * (1 - g[i]) for m in airports if m != j)   <= quicksum(z[k, i, j] * aircraft_properties[k]['Seats'] * aircraft_properties[k]['LF'] for k in aircraft_types),  name=f"Capacity_{i}_{j}")

print("Capacity Constraints (C2) added successfully.")

# Flow Balance Constraint (C3)
for k in aircraft_types:
    for i in airports:
        model.addConstr(quicksum(z[k, i, j] for j in airports if j != i) == quicksum(z[k, j, i] for j in airports if j != i), name=f"FlowBalance_{k}_{i}") 

print("Flow Balance Constraints (C3) added successfully.")


# Total Time Constraint (C4)
for k in aircraft_types:
    model.addConstr(
        quicksum(
            ((distance_matrix[i][j] / aircraft_properties[k]['Speed']) +  aircraft_properties[k]['TAT'] / 60 * ( 1 + 0.5 * (1- g[j]))) * z[k, i, j]  
            for i in airports for j in airports if i != j
        ) <= aircraft_properties[k]['BT'] * AC[k], 
        name=f"TotalTime_{k}"
    )



# Print confirmation
print("Total Time Constraints (C4) added successfully.")

# Range Constraint (C5)
for k in aircraft_types:
    for i in airports:
        for j in airports:
            if i != j:  
                a_kij = 100000 if distance_matrix[i][j] <= aircraft_properties[k]['Max_Range'] else 0
                model.addConstr(
                    z[k, i, j] <= a_kij,
                    name=f"RangeConstraint_{k}_{i}_{j}"
                )

for k in aircraft_types:
    for i in airports:
        for j in airports:
            if i != j:
                
                runway_requirement = aircraft_properties[k]['Runway Requirement']
                min_runway_length = min(runway_lengths[i], runway_lengths[j])

                
                if min_runway_length >= runway_requirement:
                    model.addConstr(y_feas[k, i, j] == 1, name=f"RunwayFeasible_{k}_{i}_{j}")
                else:
                    model.addConstr(y_feas[k, i, j] == 0, name=f"RunwayNotFeasible_{k}_{i}_{j}")

                
                model.addConstr(z[k, i, j] <= 1000 * y_feas[k, i, j], name=f"RunwayLink_{k}_{i}_{j}")





 
for i in airports:
    for j in airports:
        if i != j:  
            model.addConstr(
                quicksum(z[k, i, j] for k in aircraft_types) <= min(available_slots[i], available_slots[j]),
                name=f"SlotLimitation_{i}_{j}"
            )


# Print confirmation
print("Slot Limitation Constraints (C7) added successfully.")

print(f"Runway Length for EPWA: {runway_lengths['EPWA']}")
print(f"Runway Requirement for Aircraft 4: {aircraft_properties['Aircraft 4']['Runway Requirement']}")

model.write("model.lp")

model.Params.TimeLimit = 25

# Optimize the model
model.optimize()

if model.status in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
    if model.status == GRB.TIME_LIMIT:
        print("\nTime limit reached. Best solution found so far:")


    if model.SolCount > 0:
        print(f"\nObjective Value: €{model.objVal:,.2f}")
    else:
        print("\nNo feasible solution found within the time limit.")


    print("\nNumber of Aircraft Leased:")
    for k in aircraft_types:
        if AC[k].x > 0:
            print(f" - {k}: {AC[k].x}")


    print("\nFlight Frequencies (Weekly):")
    for k in aircraft_types:
        for i in airports:
            for j in airports:
                if i != j and z[k, i, j].x > 0:  
                    print(f"{k}: {i} → {j}, Flights: {z[k, i, j].x}")


    total_flights = 0
    total_flight_time = 0
    for k in aircraft_types:
        for i in airports:
            for j in airports:
                if i != j and z[k, i, j].x > 0:
                    total_flights += z[k, i, j].x
                    flight_time = distance_matrix[i][j] / aircraft_properties[k]['Speed']
                    total_flight_time += flight_time * z[k, i, j].x

    avg_flight_time = total_flight_time / total_flights if total_flights > 0 else 0
    print(f"\nTotal Number of Flights: {int(total_flights)}")
    print(f"Average Flight Time: {avg_flight_time:.2f} hours")

   
    print("\nOperational Hours per Aircraft Type:")
    for k in aircraft_types:
        total_hours = 0
        for i in airports:
            for j in airports:
                if i != j and z[k, i, j].x > 0:
                    flight_time = distance_matrix[i][j] / aircraft_properties[k]['Speed']
                    turnaround_time = aircraft_properties[k]['TAT'] / 60
                    total_hours += (flight_time + turnaround_time) * z[k, i, j].x

        total_hours_all_aircraft = total_hours / AC[k].x if AC[k].x > 0 else 0
        max_hours = aircraft_properties[k]['BT']
        print(f" - {k}: {total_hours_all_aircraft:.2f} hours per aircraft "
              f"(Max: {max_hours} hours, Used: {total_hours_all_aircraft/max_hours:.1%})")

    
    total_distance = 0
    total_flights = 0
    for k in aircraft_types:
        for i in airports:
            for j in airports:
                if i != j and z[k, i, j].x > 0:
                    total_flights += z[k, i, j].x
                    total_distance += distance_matrix[i][j] * z[k, i, j].x

    avg_distance = total_distance / total_flights if total_flights > 0 else 0
    print(f"\nTotal Distance Traveled: {total_distance:.2f} km")
    print(f"Total Number of Flights: {int(total_flights)}")
    print(f"Average Distance of Flights: {avg_distance:.2f} km")
else:
    print("\nNo solution found or model did not terminate successfully.")
