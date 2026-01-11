from geopy.distance import geodesic

def is_within_geofence(user_coords, office_coords, threshold):
    """
    Calculates if the distance between user and office is within the threshold.
    user_coords: (lat, lon)
    office_coords: (lat, lon)
    threshold: distance in meters
    """
    distance = geodesic(user_coords, office_coords).meters
    return distance <= threshold, distance