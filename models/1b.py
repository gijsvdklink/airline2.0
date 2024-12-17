import pandas as pd
from gurobipy import Model, GRB, quicksum

# Load data
demand_data = pd.read_excel('Future_Demand_2025_with_Gravity_Model.xlsx', index_col=0)
distance_data = pd.read_csv('distance_matrix_with_city_names.csv', index_col=0)

# Path to the Excel file
data_file_path = 'data/DemandGroup16.xlsx'

# Load the airport_data sheet (skipping irrelevant rows)
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



#vanaf hier verder coderen.

# Define sets and parameters
airports = list(demand_data.index)  # List of airports (N)
aircraft_types = list(aircraft_data['Type'])  # List of aircraft types (K)

# Define g: Binary parameter indicating whether an airport is the hub
# g[i] = 0 if i is the hub (e.g., 'EDDF'), 1 otherwise
hub_airport = 'EDDF'  # Set the hub airport
g = {airport: 0 if airport == hub_airport else 1 for airport in airports}

# Print g for verification
print("Hub binary parameter (g):", g)

# Define parameters
distance_matrix = distance_data.to_dict()  # Convert distance data to dictionary format
demand_matrix = demand_data.to_dict()  # Convert demand data to dictionary format

print("Airports (N):", airports)
print("Aircraft Types (K):", aircraft_types)

# Example of accessing parameters
print("Distance from EGLL to EHAM:", distance_matrix['EHAM']['EGLL'])
print("Weekly demand from EGLL to EHAM:", demand_matrix['EHAM']['EGLL'])




# Define aircraft type properties as dictionaries
aircraft_properties = {
    row['Type']: {
        'Speed': row['Speed'],                # Speed in km/h
        'Seats': row['Seats'],                # Number of seats
        'TAT': row['TAT'],                    # Turn-Around Time in minutes
        'Max_Range': row['Max_Range'],        # Maximum range in km
        'Runway Requirement': row['RQ'],      # Runway required in meters
        'Lease_Cost': row['Lease_Cost'],      # Weekly lease cost in EUR
        'Fixed_Cost': row['Fixed_Cost'],      # Fixed operating cost in EUR
        'Time_Cost': row['Time_Cost'],        # Time cost parameter in EUR/hr
        'Fuel_Cost': row['Fuel_Cost'],        # Fuel cost parameter
        'LF': row['LF'],                      # Load Factor
        'BT': row['BT']                       # Maximum daily operational hours
    }
    for _, row in aircraft_data.iterrows()
}



print("Aircraft Properties:", aircraft_properties)

# Set the correct column headers to be the airport codes (row 1 in the image)
airport_data.columns = airport_data.iloc[1]  # Use row 1 (index 1) as column names
airport_data = airport_data.drop([0, 1], axis=0)  # Remove the first two rows (metadata)

# Remove the 'ICAO Code' column
airport_data = airport_data.drop(columns=['ICAO Code'])

# Extract runway lengths and available slots
runway_lengths = airport_data.loc[4].to_dict()  # Row 4: Runway Lengths
available_slots = airport_data.loc[5].to_dict()  # Row 5: Available Slots

# Remove NaN or irrelevant keys
runway_lengths = {key: value for key, value in runway_lengths.items() if pd.notna(value)}
available_slots = {key: value for key, value in available_slots.items() if pd.notna(value)}

# Print the results
print("Runway Lengths:", runway_lengths)
print("Available Slots:", available_slots)



#code from here

model = Model('Fleet_and_Network_Planning')  # Create the optimization model


# Explicit naming for variables
# Decision variables
x = model.addVars(airports, airports, name="x_ij", lb=0, vtype=GRB.INTEGER)
z = model.addVars(aircraft_types, airports, airports, name="z_kij", lb=0, vtype=GRB.INTEGER)  # Weekly flights
w = model.addVars(airports, airports, name="w_ij", lb=0, vtype=GRB.INTEGER)  # Transfer passengers
AC = model.addVars(aircraft_types, name="AC_k", lb=0, vtype=GRB.INTEGER)  # Aircraft leased
y = model.addVars(aircraft_types, airports, vtype=GRB.BINARY, name="y_ki")
y_feas = model.addVars(aircraft_types, airports, airports, vtype=GRB.BINARY, name="y_feas_kij")


# Print variable structure for verification
print("Decision Variables defined:")
print("x_ij[i,j]: Direct flow of passengers on route i → j (integer)")
print("z_kij[k,i,j]: Weekly flights operated by aircraft type k from i to j (integer)")
print("w_ij[i,j]: Transfer passenger flow (integer)")
print("AC_k[k]: Number of aircraft of type k leased (integer)")

# Calculate yields for each route
def calculate_yield(distance):
    return 5.9 * (distance ** -0.76) + 0.043

# Pre-calculate yields
yields = {
    (i, j): calculate_yield(distance_matrix[j][i]) for i in airports for j in airports if i != j
}

def calculate_cost(fixed_cost, time_cost, fuel_cost, speed, distance, i, j, g, fuel_price=1.42):
    base_cost = fixed_cost + (time_cost * distance / speed) + (fuel_cost * fuel_price * distance / 1.5)
    if (1 - g[i]) + (1 - g[j]) > 0:  # Hub condition
        return 0.7 * base_cost
    else:
        return base_cost


flight_costs = {
    (k, i, j): calculate_cost(
        aircraft_properties[k]['Fixed_Cost'],
        aircraft_properties[k]['Time_Cost'],
        aircraft_properties[k]['Fuel_Cost'],
        aircraft_properties[k]['Speed'],
        distance_matrix[j][i],  # Pass the distance
        i,  # Current airport
        j,  # Destination airport
        g   # Hub binary parameter
    )
    for k in aircraft_types for i in airports for j in airports if i != j
}




# Objective function components
profit_revenue = quicksum(
    yields[i, j] * distance_matrix[j][i] * (x[i, j] + w[i, j])
    for i in airports for j in airports if i != j
)

cost_flight = quicksum(
    z[k, i, j] * flight_costs[k, i, j]
    for k in aircraft_types for i in airports for j in airports if i != j
)

cost_leasing = quicksum(
    AC[k] * aircraft_properties[k]['Lease_Cost'] for k in aircraft_types
)

# Define the objective function
model.setObjective(profit_revenue - cost_flight - cost_leasing, GRB.MAXIMIZE)



# Print confirmation
print("Objective function added successfully.")

# Weekly Demand Constraint (C1)
for i in airports:
    for j in airports:
        if i != j:  # Exclude same airport pairs
            model.addConstr(
                x[i, j] + w[i, j] <= demand_matrix[j][i],  # Demand is defined in the matrix
                name=f"Demand_{i}_{j}"
            )

# Print confirmation
print("Weekly demand (C1) added successfully.")



for i in airports:
    for j in airports:
        if i != j:  # Exclude same airport pairs
            model.addConstr(
                w[i, j] <= demand_matrix[j][i] * g[i] * g[j],
                name=f"TransferPassenger_{i}_{j}"
            )


# Print confirmation
print("Transfer Passenger Constraints (C1*) added successfully with HUB = EDDF.")

# Weekly Capacity Constraint (C2)
for i in airports:
    for j in airports:
        if i != j:  # Exclude same airport pairs
            model.addConstr(
                x[i, j] +  # Direct passenger flow from i to j
                quicksum(w[i, m] * (1 - g[j]) for m in airports if m != i) +  # Incoming transfer passengers to j
                quicksum(w[m, i] * (1 - g[i]) for m in airports if m != j)   # Outgoing transfer passengers from i
                <= quicksum(z[k, i, j] * aircraft_properties[k]['Seats'] * aircraft_properties[k]['LF'] for k in aircraft_types),  # Summed over aircraft types
                name=f"Capacity_{i}_{j}"
            )
# Print confirmation
print("Capacity Constraints (C2) added successfully.")

# Flow Balance Constraint (C3)
for k in aircraft_types:
    for i in airports:
        model.addConstr(
            quicksum(z[k, i, j] for j in airports if j != i) == quicksum(z[k, j, i] for j in airports if j != i),
            name=f"FlowBalance_{k}_{i}"
        ) 

# Print confirmation
print("Flow Balance Constraints (C3) added successfully.")


# Precompute hub adjustment factors
hub_adjustment = {j: 1 + 0.5 * g[j] for j in airports}

# Total Time Constraint (C4)
for k in aircraft_types:
    model.addConstr(
        quicksum(
            (
                (distance_matrix[i][j] / aircraft_properties[k]['Speed']) +  # Flight time
                aircraft_properties[k]['TAT'] / 60 * ( 1 + 0.5 * (1- g[j]))    # Turnaround time and hub adjustment
            ) * z[k, i, j]  # Total time for aircraft k between airports i and j
            for i in airports for j in airports if i != j
        ) <= aircraft_properties[k]['BT'] * AC[k],  # Total time should be less than or equal to available time
        name=f"TotalTime_{k}"
    )





# Print confirmation
print("Total Time Constraints (C4) added successfully.")

# Range Constraint (C5)
for k in aircraft_types:
    for i in airports:
        for j in airports:
            if i != j:  # Exclude same airport pairs
                a_kij = 100000 if distance_matrix[i][j] <= aircraft_properties[k]['Max_Range'] else 0
                model.addConstr(
                    z[k, i, j] <= a_kij,
                    name=f"RangeConstraint_{k}_{i}_{j}"
                )

for k in aircraft_types:
    for i in airports:
        for j in airports:
            if i != j:
                # Check the minimum runway length and required runway length
                runway_requirement = aircraft_properties[k]['Runway Requirement']
                min_runway_length = min(runway_lengths[i], runway_lengths[j])

                # Enforce the feasibility binary variable y_feas
                if min_runway_length >= runway_requirement:
                    model.addConstr(y_feas[k, i, j] == 1, name=f"RunwayFeasible_{k}_{i}_{j}")
                else:
                    model.addConstr(y_feas[k, i, j] == 0, name=f"RunwayNotFeasible_{k}_{i}_{j}")

                # Link feasibility to flight variable z[k,i,j]
                model.addConstr(z[k, i, j] <= 1000 * y_feas[k, i, j], name=f"RunwayLink_{k}_{i}_{j}")





 # Slot Limitation Constraint (C7)
for i in airports:
    for j in airports:
        if i != j:  # Exclude same airport pairs
            model.addConstr(
                quicksum(z[k, i, j] for k in aircraft_types) <= min(available_slots[i], available_slots[j]),
                name=f"SlotLimitation_{i}_{j}"
            )


# Print confirmation
print("Slot Limitation Constraints (C7) added successfully.")

print(f"Runway Length for EPWA: {runway_lengths['EPWA']}")
print(f"Runway Requirement for Aircraft 4: {aircraft_properties['Aircraft 4']['Runway Requirement']}")

model.optimize()

if model.status == GRB.OPTIMAL:
    # Print the optimal objective value
    print(f"\nOptimal Objective Value: €{model.objVal:,.2f}")

    # Print the leased aircraft of each type
    print("\nNumber of Aircraft Leased:")
    for k in aircraft_types:
        print(f" - {k}: {AC[k].x}")

    # Print the operated network (flight frequencies)
    print("\nFlight Frequencies (Weekly):")
    for k in aircraft_types:
        for i in airports:
            for j in airports:
                if i != j and z[k, i, j].x > 0:  # Only show flights with non-zero frequency
                    print(f"Aircraft {k}: {i} → {j}, Flights: {z[k, i, j].x}")


else:
    print("\nNo optimal solution found.")


if model.status == GRB.OPTIMAL:
    total_flights = 0
    total_flight_time = 0

    # Loop through all aircraft types and airport pairs to calculate total flights and total flight time
    for k in aircraft_types:
        for i in airports:
            for j in airports:
                if i != j and z[k, i, j].x > 0:  # Only consider non-zero flights
                    total_flights += z[k, i, j].x  # Total number of flights
                    flight_time = distance_matrix[i][j] / aircraft_properties[k]['Speed']  # Flight time
                    total_flight_time += flight_time * z[k, i, j].x  # Add weighted flight time

    # Calculate average flight time
    if total_flights > 0:
        avg_flight_time = total_flight_time / total_flights
    else:
        avg_flight_time = 0

    # Print results
    print(f"\nTotal Number of Flights: {int(total_flights)}")
    print(f"Average Flight Time: {avg_flight_time:.2f} hours")
else:
    print("No optimal solution found.")


if model.status == GRB.OPTIMAL:
    print("\nOperational Hours per Aircraft Type (Optimal Solution):")
    
    for k in aircraft_types:
        total_hours = 0
        
        # Calculate operational hours
        for i in airports:
            for j in airports:
                if i != j and z[k, i, j].x > 0:  # Only consider active routes
                    flight_time = distance_matrix[i][j] / aircraft_properties[k]['Speed']  # Flight time in hours
                    turnaround_time = aircraft_properties[k]['TAT'] / 60  # Turnaround time in hours
                    total_hours += (flight_time + turnaround_time) * z[k, i, j].x  # Total time
        
        # Total hours for all leased aircraft of type k
        total_hours_all_aircraft = total_hours / AC[k].x if AC[k].x > 0 else 0
        
        # Print the result for the current aircraft type
        max_hours = aircraft_properties[k]['BT']  # Maximum allowed operational hours per aircraft
        print(f" - {k}: {total_hours_all_aircraft:.2f} hours per aircraft "
              f"(Max: {max_hours} hours, Used: {total_hours_all_aircraft/max_hours:.1%})")
else:
    print("No optimal solution found.")

if model.status == GRB.OPTIMAL:
    total_distance = 0
    total_flights = 0

    # Loop through all aircraft types and airport pairs
    for k in aircraft_types:
        for i in airports:
            for j in airports:
                if i != j and z[k, i, j].x > 0:  # Only consider active flights
                    total_flights += z[k, i, j].x  # Add the number of flights
                    total_distance += distance_matrix[i][j] * z[k, i, j].x  # Add the distance traveled

    # Calculate the average distance
    if total_flights > 0:
        avg_distance = total_distance / total_flights
    else:
        avg_distance = 0

    # Print results
    print(f"\nTotal Distance Traveled: {total_distance:.2f} km")
    print(f"Total Number of Flights: {int(total_flights)}")
    print(f"Average Distance of Flights: {avg_distance:.2f} km")
else:
    print("No optimal solution found.")
