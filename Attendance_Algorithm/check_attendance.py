import asyncio
import json
import numpy as np
from pathlib import Path

from .src import initialize_check, process_captured_image, BiometricEngine

DATA_PATH = (
    Path(__file__).resolve()
    .parent / "data" / "employees_biometric_with_names.json"
)

engine = BiometricEngine()


# -------------------------
# Helpers
# -------------------------
def _load_employees():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)   # dict keyed by emp_id


def _generate_embedding(face):
    return engine.generate_embedding(face)


def _compute_avg_similarity(live_vec, ref_embeddings):
    similarities = [
        engine.compute_similarity(live_vec, np.array(v))
        for v in ref_embeddings
    ]
    return float(np.mean(similarities))


async def verify_attendance(emp_id: str, current_gps: tuple, live_photo_path: str):
    print(f"\n--- Starting Attendance Session for {emp_id} ---")

    employees = _load_employees()

    if emp_id not in employees:
        return {
            "status": "error",
            "message": f"Employee {emp_id} not found"
        }

    emp_record = employees[emp_id]

    # 🔹 STEP 1: Geo verification
    geo_result = await initialize_check(emp_id, current_gps)
    if geo_result["status"] != "success":
        return {
            "status": "geo_failed",
            "message": geo_result["message"]
        }

    loop = asyncio.get_running_loop()

    # 🔹 STEP 2: Image processing (CPU → thread)
    img_result = await loop.run_in_executor(
        None,
        process_captured_image,
        live_photo_path
    )

    if img_result["status"] == "update_required":
        return img_result

    if img_result["status"] != "success":
        return {
            "status": "failed",
            "message": img_result["message"]
        }

    live_face = img_result["processed_face"]

    # 🔹 STEP 3: Embedding generation
    live_vec = await loop.run_in_executor(
        None,
        _generate_embedding,
        live_face
    )

    ref_embeddings = emp_record.get("face_embeddings", [])
    if not ref_embeddings:
        return {
            "status": "error",
            "message": "No reference embeddings found"
        }

    # 🔹 STEP 4: Similarity computation
    avg_similarity = await loop.run_in_executor(
        None,
        _compute_avg_similarity,
        live_vec,
        ref_embeddings
    )

    THRESHOLD = 0.70
    match = avg_similarity >= THRESHOLD

    print(
        f"{'VERIFIED' if match else 'REJECTED'} | "
        f"Avg Similarity: {avg_similarity:.4f}"
    )

    return {
        "status": "success" if match else "rejected",
        "emp_id": emp_id,
        "name": emp_record.get("name"),
        "department": emp_record.get("department"),
        "average_similarity": round(avg_similarity, 4),
        "match": bool(match)
    }
