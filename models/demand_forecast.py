import sys
import os


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np


data_file_path = 'data/DemandGroup16.xlsx'
airport_data = pd.read_excel(data_file_path, sheet_name='airport_data', header=None, usecols=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]) 
airport_data_transposed = airport_data.transpose()
airport_data_transposed.columns = airport_data_transposed.iloc[0]
airport_data_transposed = airport_data_transposed[1:]
demand_per_week = pd.read_excel(data_file_path, sheet_name='demand_per_week', header=None, usecols=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21])


demand_per_week.columns = demand_per_week.iloc[0]  
demand_per_week = demand_per_week[1:]  
demand_per_week.index = demand_per_week.iloc[:, 0]  
demand_per_week = demand_per_week.iloc[:, 1:]  
demand_per_week = demand_per_week.apply(pd.to_numeric, errors='coerce')  


pop_data = pd.read_excel('data/pop.xlsx', usecols=[0, 1, 2, 4, 5, 6], skiprows=[0, 1])

pop_data[2020] = pd.to_numeric(pop_data[2020])
pop_data[2023] = pd.to_numeric(pop_data[2023])
pop_data['2020.1'] = pd.to_numeric(pop_data['2020.1'])
pop_data['2023.1'] = pd.to_numeric(pop_data['2023.1'])


print("\nPopulation and GDP Data:")
print(pop_data)
print("\nTransposed Airport Data:")
print(airport_data_transposed)
print("\nDemand Per Week Data:")
print(demand_per_week)

import sys
from utils.distance_calculations import calculate_distance, calculate_distance_matrix


latitudes = airport_data_transposed['Latitude (deg)'].astype(float).values
longitudes = airport_data_transposed['Longitude (deg)'].astype(float).values
city_names = airport_data_transposed['ICAO Code'].tolist()

distance_matrix = calculate_distance_matrix(latitudes, longitudes)
distance_df = pd.DataFrame(distance_matrix, index=city_names, columns=city_names)


distance_df = distance_df.round(1)
print("\nDistance Matrix from airport i to airport j [km]:")
print(distance_df)

demand_2020 = demand_per_week.values  
print(demand_2020)

num_cities = len(pop_data)

log_pop_sum = []  # X1 = ln(Pi) + ln(Pj)
log_gdp_sum = []  # X2 = ln(GDPi) + ln(GDPj)
log_fuel_distance = []  # X3 = ln(f) + ln(dij)
log_demand = []  # Y = ln(Dij)


fuel_cost = 1.42
log_fuel_cost = np.log(fuel_cost)

#only use triangle above diagonal
for i, j in zip(*np.triu_indices(num_cities, k=1)):  
    
    log_pop_sum.append(np.log(pop_data.loc[i, 2020]) + np.log(pop_data.loc[j, 2020]))
    log_gdp_sum.append(np.log(pop_data.loc[i, '2020.1']) + np.log(pop_data.loc[j, '2020.1']))
    log_fuel_distance.append(log_fuel_cost + np.log(distance_df.iloc[i, j]))
    log_demand.append(np.log(demand_2020[i, j]))


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


y = log_demand

#ordinary least squares calculation beta
XT_X = np.dot(X.T, X)  
XT_y = np.dot(X.T, y)  
beta = np.linalg.inv(XT_X).dot(XT_y)  

print(beta)
ln_k = beta[0]  
k = np.exp(ln_k)  
b1 = beta[1]  
b2 = beta[2] 
b3 = -beta[3]  


print("Calibration Results:")
print(f"Scaling Factor k: {k}")
print(f"Coefficient b1 (Population): {b1}")
print(f"Coefficient b2 (GDP): {b2}")
print(f"Coefficient b3 (Distance): {b3}")


real_demand = demand_2020[np.triu_indices(20, k=1)]  # 20 is het aantal steden

import matplotlib.pyplot as plt
import numpy as np


estimated_log_demand = (
    beta[0] +  # ln(k)
    beta[1] * log_pop_sum +  # b1 * ln(Pi * Pj)
    beta[2] * log_gdp_sum +  # b2 * ln(GDPi * GDPj)
    beta[3] * log_fuel_distance  # -b3 * ln(f * dij)
)


estimated_demand = np.exp(estimated_log_demand)


if real_demand.shape != estimated_demand.shape:
    raise ValueError("different shapes.")


plt.figure(figsize=(10, 6))
plt.scatter(real_demand, estimated_demand, alpha=0.7, color='blue', label="Estimated Demand")
plt.plot(
    [0, max(real_demand.max(), estimated_demand.max())], 
    [0, max(real_demand.max(), estimated_demand.max())], 
    color='red', linestyle='--', label="Perfect Line (y=x)"
)

plt.title("Comparison of Actual and Estimated Demand (2020)")
plt.xlabel("Actual Demand (D_ij)")
plt.ylabel("Estimated Demand (D_ij)")
plt.legend()
plt.grid(True)
plt.show()





# Average Annual Growth calculation
pop_data['AAG_Population'] = (pop_data[2023] / pop_data[2020]) ** (1/3) - 1 #this is the grow factor for one year
pop_data['AAG_GDP'] = (pop_data['2023.1'] / pop_data['2020.1']) ** (1/3) - 1
pop_data[2025] = (pop_data[2023] * ((1 + pop_data['AAG_Population']))**2).round(0).astype(int)
pop_data['2025.1'] = (pop_data['2023.1'] * ((1 + pop_data['AAG_GDP']))**2).round(0).astype(int)




future_demand = np.zeros((num_cities, num_cities))

for i in range(num_cities):
    for j in range(num_cities):
        if i != j:  # Skip self-loops
            pop_i = pop_data.loc[i, 2025]
            pop_j = pop_data.loc[j, 2025]
            gdp_i = pop_data.loc[i, '2025.1']
            gdp_j = pop_data.loc[j, '2025.1']
            distance = distance_df.iloc[i, j]
            future_demand[i, j] = (k * ((pop_i * pop_j) ** b1) * ((gdp_i * gdp_j) ** b2) / ((fuel_cost * distance) ** b3))


future_demand = np.round(future_demand).astype(int) #should be integers
city_names = distance_df.index  
future_demand_df = pd.DataFrame(future_demand, index=city_names, columns=city_names)


future_demand_df.index.name = "Origin"
future_demand_df.columns.name = "Destination"
print("\nFuture Demand for 2025 (Terminal Output):")
print(future_demand_df)


output_file = "Future_Demand_2025.xlsx"
future_demand_df.to_excel(output_file)

print(f"\nFuture demand for 2025 calculated and saved to {output_file}.")

