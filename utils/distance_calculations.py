import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the great-circle distance between two points using the formula from Appendix C.
    Inputs are in decimal degrees.
    """
    # Radius of Earth in kilometers
    R = 6371

    # Convert degrees to radians
    lat1, lon1 = math.radians(lat1), math.radians(lon1)
    lat2, lon2 = math.radians(lat2), math.radians(lon2)

    # Compute the differences
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    # Apply the formula
    a = math.sin(delta_lat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2)**2
    delta_sigma = 2 * math.asin(math.sqrt(a))
    distance = R * delta_sigma

    return distance

def calculate_distance_matrix(latitudes, longitudes):
    """
    Compute the pairwise distance matrix for all airports.

    Parameters:
        latitudes: List or array of latitudes for all airports.
        longitudes: List or array of longitudes for all airports.

    Returns:
        A 2D list where element (i, j) is the distance between airport i and airport j.
    """
    num_airports = len(latitudes)
    distance_matrix = [[0 for _ in range(num_airports)] for _ in range(num_airports)]

    for i in range(num_airports):
        for j in range(num_airports):
            if i != j:  # Avoid recalculating for the same airport
                distance_matrix[i][j] = calculate_distance(latitudes[i], longitudes[i], latitudes[j], longitudes[j])

    return distance_matrix
