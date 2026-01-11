import json
import warnings
from pathlib import Path

from .src.preprocessing import process_captured_image
from .src.biometric_engine import BiometricEngine

warnings.filterwarnings("ignore")

# -------------------------
# CONFIG
# -------------------------
DATA_PATH = (
    Path(__file__).resolve()
    .parent / "data" / "employees_biometric_with_names.json"
)

engine = BiometricEngine()


# -------------------------
# UTILS
# -------------------------
def _load_employees():
    if not DATA_PATH.exists():
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_employees(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# -------------------------
# MAIN FUNCTION
# -------------------------
def register_employee(
    emp_id,
    name,
    department,
    office_lat,
    office_lon,
    geo_threshold,
    image_paths
):
    """
    Processes 5 images, generates embeddings, and saves profile to local JSON.
    """

    print(f"--- Starting Biometric Registration for {emp_id} ({name}) ---")

    if len(image_paths) != 5:
        return {
            "status": "error",
            "message": "Exactly 5 images are required for registration."
        }

    all_embeddings = []

    for idx, path in enumerate(image_paths):
        result = process_captured_image(path)

        if result["status"] != "success":
            return {
                "status": "error",
                "message": f"Image {idx + 1} failed processing: {result.get('message')}"
            }

        face_img = result["processed_face"]
        embedding = engine.generate_embedding(face_img)
        all_embeddings.append(embedding.tolist())

    # Load existing JSON
    employees = _load_employees()

    # Upsert employee
    employees[emp_id] = {
        "name": name,
        "department": department,
        "office_lat": float(office_lat),
        "office_lon": float(office_lon),
        "geo_threshold_meters": int(geo_threshold),
        "face_embeddings": all_embeddings
    }

    # Save back to JSON
    _save_employees(employees)

    print(f"✅ Registration Successful: {emp_id} saved to local JSON.")

    return {
        "status": "success",
        "emp_id": emp_id,
        "message": "User registered successfully (local JSON)."
    }
