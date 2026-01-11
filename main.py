from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import uvicorn
import warnings
from typing import Tuple
import os

warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import shutil
from Attendance_Algorithm import verify_attendance as check_attendance_logic
from Agentics import run_progress_workflow, meeting_planner, GrievanceApplication, process_complaints, GrievanceVerdictRequest, process_grievance_verdict, TransferApplication, process_transfer_request, TransferVerdictRequest, process_manager_verdict, QueryRequest, StartRequest, SelectSlotRequest, graph_app
from Attendance_Algorithm import register_employee

def make_initial_state(emp_id: str, task: str, description: str = ""):
    return {
        "emp_id": emp_id,
        "task": task,
        "description": description,
        "planner_outcome": None,
        "selected_slot": None,
        "final_status": None
    }

app = FastAPI(title="HR System API")

@app.post("/grievance/submit")
async def submit_grievance(data: GrievanceApplication):
    # In production, employee_summary would be fetched from DB via emp_id
    summary = "Mock: Employee has 90% trust index, no current PIP."
    result = process_complaints(data, summary)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.post("/grievance/admin-action")
async def admin_action(req: GrievanceVerdictRequest):
    result = process_grievance_verdict(
        emp_id=req.emp_id, 
        verdict=req.verdict, 
        manager_notes=req.manager_notes
    )
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/transfer/submit")
async def api_submit_transfer(app_data: TransferApplication):
    """Employee submits a new request."""
    result = process_transfer_request(app_data)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.post("/transfer/verdict")
async def api_admin_verdict(data: TransferVerdictRequest):
    """Admin reviews and decides on the request."""
    result = process_manager_verdict(
        emp_id=data.emp_id, 
        verdict=data.verdict, 
        manager_notes=data.manager_notes
    )
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/generate-progress-report")
async def generate_report(request: QueryRequest):
    """
    Endpoint to trigger the LangGraph workflow.
    Input: {"user_query": "Plan a meet with employee E1012"}
    """
    try:
        if not request.user_query:
            raise HTTPException(status_code=400, detail="User query cannot be empty.")

        progress_report = await run_progress_workflow(request.user_query)

        return {
            "status": "success",
            "progress_report": progress_report
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow Error: {str(e)}")

@app.post("/register")
async def api_register(
    emp_id: str = Form(...),
    name: str = Form(...),
    dept: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    threshold: int = Form(...),
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
            if os.path.exists(p):
                os.remove(p)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@app.post("/attendance-check")
async def attendance_endpoint(
    emp_id: str = Form(...), 
    gps_x: float = Form(...), 
    gps_y: float = Form(...), 
    file: UploadFile = File(...)
):
    gps = (gps_x, gps_y)
    temp_path = f"temp_{file.filename}"
    
    try:
        # Save the file
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 1. Ensure you are calling the CORRECT function name
        # 2. Add 'await' if your logic function is async
        result = await check_attendance_logic(emp_id, gps, temp_path)

        return result

    finally:
        # Using finally ensures the file is deleted even if the logic fails
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/meeting/initiate")
async def initiate_meeting(req: StartRequest):
    config = {"configurable": {"thread_id": req.emp_id}}

    initial_state = make_initial_state(
        emp_id=req.emp_id,
        task=req.task,
        description=req.description
    )

    # Run until interrupt
    await graph_app.ainvoke(initial_state, config=config)

    state = graph_app.get_state(config)

    planner_outcome = state.values["planner_outcome"]

    return {
        "thread_id": req.emp_id,
        "options": planner_outcome.proposed_slots,
        "agenda": planner_outcome.meeting_agenda
    }

@app.post("/meeting/confirm")
async def confirm_meeting(req: SelectSlotRequest):
    config = {"configurable": {"thread_id": req.thread_id}}

    # Update paused state
    graph_app.update_state(
        config,
        {"selected_slot": req.selected_slot}
    )

    # Resume execution
    await graph_app.ainvoke(None, config=config)

    final_state = graph_app.get_state(config)

    return {
        "status": final_state.values["final_status"]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
