import json
import cv2
import numpy as np
from pathlib import Path

from src import BiometricEngine

# -------------------------
# CONFIG
# -------------------------
DATA_PATH = Path(r"Attendance_Algorithm\data\employees_biometric_with_names.json")

# Single image used for demo (same for all employees)
# You can replace this with different images later
IMAGE_PATH = Path(r"Attendance_Algorithm\test_images\WhatsApp Image 2026-01-09 at 8.03.51 PM.jpeg")

NUM_EMBEDDINGS = 5  # required

# -------------------------
# LOAD ENGINE
# -------------------------
engine = BiometricEngine()

# -------------------------
# LOAD IMAGE
# -------------------------
image = cv2.imread(str(IMAGE_PATH))
if image is None:
    raise FileNotFoundError(f"Image not found at {IMAGE_PATH}")

# Resize to model input size (safety)
image = cv2.resize(image, (112, 112))

# -------------------------
# GENERATE EMBEDDING
# -------------------------
embedding = engine.generate_embedding(image)  # shape (192,)
embedding_list = embedding.tolist()

# -------------------------
# LOAD JSON
# -------------------------
with open(DATA_PATH, "r", encoding="utf-8") as f:
    employees = json.load(f)

# -------------------------
# UPDATE EACH EMPLOYEE
# -------------------------
for emp_id, emp_data in employees.items():
    emp_data["face_embeddings"] = [embedding_list] * NUM_EMBEDDINGS

# -------------------------
# SAVE JSON
# -------------------------
with open(DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(employees, f, indent=2)

print("✅ face_embeddings populated successfully (192-d × 5)")
