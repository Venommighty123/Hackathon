import json
from pathlib import Path
from .utils.geo_utils import is_within_geofence

DATA_PATH = (
    Path(__file__).resolve()
    .parent.parent / "data" / "employees_biometric_with_names.json"
)


def _load_employees():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)   # <-- returns dict


async def initialize_check(employee_id: str, current_gps: tuple):
    """
    Step 1: Fetch employee from JSON and verify GPS geofence
    """

    employees = _load_employees()

    if employee_id not in employees:
        return {
            "status": "error",
            "message": "Employee ID not found"
        }

    emp_data = employees[employee_id]

    office_coords = (
        emp_data["office_lat"],
        emp_data["office_lon"]
    )

    is_valid, actual_distance = is_within_geofence(
        current_gps,
        office_coords,
        emp_data["geo_threshold_meters"]
    )

    if not is_valid:
        return {
            "status": "failed",
            "message": f"Outside geofence. Distance: {actual_distance:.2f}m",
            "next_step": "Update Request"
        }

    return {
        "status": "success",
        "message": "GPS Verified",
        "emp_data": emp_data,
        "next_step": "Image Checking Algorithm"
    }
