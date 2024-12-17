import sys
import os

# Add the parent directory of `models` to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np

# Path to the Excel file
data_file_path = 'data/DemandGroup16.xlsx'

# Load the airport_data sheet (skipping irrelevant rows)
airport_data = pd.read_excel(data_file_path, sheet_name='airport_data', header=None, usecols=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21])  # Include the desired columns

# Transpose the airport_data
airport_data_transposed = airport_data.transpose()

# Set the first row as the column headers
airport_data_transposed.columns = airport_data_transposed.iloc[0]

# Drop the first row (it’s now redundant)
airport_data_transposed = airport_data_transposed[1:]

# Load demand_per_week sheet with all rows
demand_per_week = pd.read_excel(data_file_path, sheet_name='demand_per_week', header=None, usecols=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21])

# Clean demand_per_week
demand_per_week.columns = demand_per_week.iloc[0]  # First row becomes column names
demand_per_week = demand_per_week[1:]  # Exclude the first row from the data
demand_per_week.index = demand_per_week.iloc[:, 0]  # First column becomes row index (origin airports)
demand_per_week = demand_per_week.iloc[:, 1:]  # Exclude the first column from data
demand_per_week = demand_per_week.apply(pd.to_numeric, errors='coerce')  # Convert values to numeric

# Load the population and GDP data
pop_data = pd.read_excel('data/pop.xlsx', usecols=[0, 1, 2, 4, 5, 6], skiprows=[0, 1])

# Convert Population and GDP columns to numeric in-place
pop_data[2020] = pd.to_numeric(pop_data[2020], errors='coerce')
pop_data[2023] = pd.to_numeric(pop_data[2023], errors='coerce')
pop_data['2020.1'] = pd.to_numeric(pop_data['2020.1'], errors='coerce')
pop_data['2023.1'] = pd.to_numeric(pop_data['2023.1'], errors='coerce')

# Preview the cleaned data
print("\nCleaned Population and GDP Data:")
print(pop_data)
print("\nCleaned Transposed Airport Data:")
print(airport_data_transposed)
print("\nCleaned Demand Per Week Data:")
print(demand_per_week)

import sys


from utils.distance_calculations import calculate_distance, calculate_distance_matrix

# Extract latitudes and longitudes
latitudes = airport_data_transposed['Latitude (deg)'].astype(float).values
longitudes = airport_data_transposed['Longitude (deg)'].astype(float).values

# Extract city names (using the ICAO Code column)
city_names = airport_data_transposed['ICAO Code'].tolist()

# Calculate the distance matrix using the imported function
distance_matrix = calculate_distance_matrix(latitudes, longitudes)

# Convert the distance matrix to a DataFrame with city names as both row and column headers
distance_df = pd.DataFrame(distance_matrix, index=city_names, columns=city_names)

# Round the values to one decimal place
distance_df = distance_df.round(1)

# Print the full distance matrix
print("\nDistance Matrix with City Names:")
print(distance_df)

# Save the full distance matrix to a CSV file
distance_df.to_csv('distance_matrix_with_city_names.csv', index=True)

# Print only distances from Frankfurt (EDDF)
print("\nDistances from Frankfurt (EDDF):")
if "EDDF" in city_names:
    distances_from_frankfurt = distance_df.loc["EDDF"]  # Extract row for Frankfurt
    print(distances_from_frankfurt)
    
    # Save Frankfurt distances to a separate CSV
    distances_from_frankfurt.to_csv('distances_from_frankfurt.csv', header=True)
else:
    print("Frankfurt (EDDF) not found in city names.")

# Small constant to avoid log(0)
# Small constant to avoid log(0)
# Zorg dat alle data geladen is
# Zorg dat alle data geladen is
# Zorg dat alle data geladen is
demand_2020 = demand_per_week.values  # Vraag D_ij als NumPy-array

# Extract aantal steden
num_cities = len(pop_data)

# Lijsten voorbereiden
log_pop_sum = []  # X1 = ln(Pi) + ln(Pj)
log_gdp_sum = []  # X2 = ln(GDPi) + ln(GDPj)
log_fuel_distance = []  # X3 = ln(f) + ln(dij)
log_demand = []  # Y = ln(Dij)

# Brandstofkosten
fuel_cost = 1.42
log_fuel_cost = np.log(fuel_cost)

# Gebruik alleen de bovenste driehoek (exclusief diagonaal)
for i, j in zip(*np.triu_indices(num_cities, k=1)):  # Bovenste driehoek
    # Bereken X1, X2, X3 en Y
    log_pop_sum.append(np.log(pop_data.loc[i, 2020]) + np.log(pop_data.loc[j, 2020]))
    log_gdp_sum.append(np.log(pop_data.loc[i, '2020.1']) + np.log(pop_data.loc[j, '2020.1']))
    log_fuel_distance.append(log_fuel_cost + np.log(distance_df.iloc[i, j]))
    log_demand.append(np.log(demand_2020[i, j]))

# Omzetten naar NumPy arrays
log_pop_sum = np.array(log_pop_sum)
log_gdp_sum = np.array(log_gdp_sum)
log_fuel_distance = np.array(log_fuel_distance)
log_demand = np.array(log_demand)


# Construct de design matrix X
X = np.column_stack([
    np.ones(len(log_demand)),  # Intercept term (C = ln(k))
    log_pop_sum,  # X1
    log_gdp_sum,  # X2
    log_fuel_distance  # X3
])

# Afhankelijke variabele Y
y = log_demand

# Bereken beta met de OLS-formule
XT_X = np.dot(X.T, X)  # X'X
XT_y = np.dot(X.T, y)  # X'y
beta = np.linalg.inv(XT_X).dot(XT_y)  # (X'X)^(-1)X'y

# Coëfficiënten interpreteren
ln_k = beta[0]  # Intercept
k = np.exp(ln_k)  # Omrekenen naar originele schaal
b1 = beta[1]  # Coëfficiënt voor populatie
b2 = beta[2]  # Coëfficiënt voor GDP
b3 = -beta[3]  # Negatief vanwege de formule

# Resultaten printen
print("Calibratie Resultaten:")
print(f"Scaling Factor k: {k}")
print(f"Coefficient b1 (Population): {b1}")
print(f"Coefficient b2 (GDP): {b2}")
print(f"Coefficient b3 (Distance): {b3}")


print(f"Demand 2020 shape: {demand_2020.shape}")
# Haal alleen de bovenste driehoek van de matrix (exclusief de diagonaal)
real_demand = demand_2020[np.triu_indices(20, k=1)]  # 20 is het aantal steden

import matplotlib.pyplot as plt
import numpy as np

# Bereken de geschatte vraagwaarden (ln(D_ij)) met het gravity model
estimated_log_demand = (
    beta[0] +  # ln(k)
    beta[1] * log_pop_sum +  # b1 * ln(Pi * Pj)
    beta[2] * log_gdp_sum +  # b2 * ln(GDPi * GDPj)
    beta[3] * log_fuel_distance  # -b3 * ln(f * dij)
)

# Zet de geschatte vraagwaarden terug naar originele schaal
estimated_demand = np.exp(estimated_log_demand)

# Controleer de shapes van real_demand en estimated_demand
print(f"Real Demand shape: {real_demand.shape}")
print(f"Estimated Demand shape: {estimated_demand.shape}")

# Zorg ervoor dat beide arrays dezelfde lengte hebben
if real_demand.shape != estimated_demand.shape:
    raise ValueError("De shapes van real_demand en estimated_demand komen niet overeen.")

# Plot de werkelijke vraag versus de geschatte vraag
plt.figure(figsize=(10, 6))
plt.scatter(real_demand, estimated_demand, alpha=0.7, color='blue', label="Geschatte vraag")
plt.plot(
    [0, max(real_demand.max(), estimated_demand.max())], 
    [0, max(real_demand.max(), estimated_demand.max())], 
    color='red', linestyle='--', label="Perfecte lijn (y=x)"
)


plt.title("Vergelijking van Werkelijke en Geschatte Vraag (2020)")
plt.xlabel("Werkelijke Vraag (D_ij)")
plt.ylabel("Geschatte Vraag (D_ij)")
plt.legend()
plt.grid(True)
plt.show()


#vanaf hier verder coderen


# Average Annual Growth calculation
pop_data['AAG_Population'] = (pop_data[2023] / pop_data[2020]) ** (1/3) - 1
pop_data['AAG_GDP'] = (pop_data['2023.1'] / pop_data['2020.1']) ** (1/3) - 1

# Forecast population and GDP for 2025
pop_data[2025] = (pop_data[2023] * (1 + pop_data['AAG_Population'])).round(0).astype(int)
pop_data['2025.1'] = (pop_data['2023.1'] * (1 + pop_data['AAG_GDP'])).round(0).astype(int)

# Future demand calculation using the gravity model
future_demand = np.zeros((num_cities, num_cities))

for i in range(num_cities):
    for j in range(num_cities):
        if i != j:  # Skip self-loops
            pop_i = pop_data.loc[i, 2025]
            pop_j = pop_data.loc[j, 2025]
            gdp_i = pop_data.loc[i, '2025.1']
            gdp_j = pop_data.loc[j, '2025.1']
            distance = distance_df.iloc[i, j]

            # Incorporate fuel costs into the gravity model
            future_demand[i, j] = (
                k * ((pop_i * pop_j) ** b1) * ((gdp_i * gdp_j) ** b2) / ((fuel_cost * distance) ** b3)
            )

# Round the demand values to integers
future_demand = np.round(future_demand).astype(int)

# Convert future demand to a DataFrame
city_names = distance_df.index  # City names from distance_df
future_demand_df = pd.DataFrame(future_demand, index=city_names, columns=city_names)

# Add row and column names
future_demand_df.index.name = "Origin"
future_demand_df.columns.name = "Destination"

# Print the future demand in the terminal
print("\nFuture Demand for 2025 (Terminal Output):")
print(future_demand_df)

# Save to Excel for presentation
output_file = "Future_Demand_2025_with_Gravity_Model.xlsx"
future_demand_df.to_excel(output_file)

print(f"\nFuture demand for 2025 calculated and saved to {output_file}.")
# Print de voorspelde populatie en GDP voor 2025 per stad
print("\nForecasted Population and GDP for 2025 per City:")
forecasted_data = pop_data[[2025, '2025.1']].rename(columns={2025: 'Population_2025', '2025.1': 'GDP_2025'})
print(forecasted_data)

# Opslaan als Excel voor presentatie
output_population_gdp_file = "Population_and_GDP_2025.xlsx"
forecasted_data.to_excel(output_population_gdp_file)

print(f"\nPopulation and GDP for 2025 saved to {output_population_gdp_file}.")


