import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

# Fix: Import directly from the folder names in your root
from Attendance_Algorithm.register_employees import register_employee
from Attendance_Algorithm.check_attendance import verify_attendance as check_attendance_logic

router = APIRouter()

@router.post("/register")
async def api_register(
    emp_id: str = Form(...), name: str = Form(...), dept: str = Form(...),
    lat: float = Form(...), lon: float = Form(...), threshold: int = Form(...),
    files: list[UploadFile] = File(...)
):
    temp_paths = []
    for i, file in enumerate(files):
        path = f"temp_reg_{emp_id}_{i}.jpg"
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        temp_paths.append(path)
    try:
        result = register_employee(emp_id, name, dept, lat, lon, threshold, temp_paths)
    finally:
        for p in temp_paths:
            if os.path.exists(p): os.remove(p)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

@router.post("/attendance-check")
async def attendance_endpoint(
    emp_id: str = Form(...), gps_x: float = Form(...), 
    gps_y: float = Form(...), file: UploadFile = File(...)
):
    gps = (gps_x, gps_y)
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return await check_attendance_logic(emp_id, gps, temp_path)
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)