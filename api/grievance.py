from fastapi import APIRouter, HTTPException
# Import directly from the Agentics folder at your root
from Agentics import (
    GrievanceApplication, 
    process_complaints, 
    GrievanceVerdictRequest, 
    process_grievance_verdict, 
    TransferApplication, 
    process_transfer_request, 
    TransferVerdictRequest, 
    process_manager_verdict
)

router = APIRouter()

@router.post("/submit")
async def submit_grievance(data: GrievanceApplication):
    """Submits a new employee grievance."""
    
    result = await process_complaints(data)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result

@router.post("/admin-action")
async def admin_action(req: GrievanceVerdictRequest):
    """Processes admin verdict on a grievance."""
    # FIX: Added 'await' here
    result = await process_grievance_verdict(
        emp_id=req.emp_id, 
        verdict=req.verdict, 
        manager_notes=req.manager_notes
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

@router.post("/transfer/submit")
async def api_submit_transfer(app_data: TransferApplication):
    """Employee submits a new transfer request."""
    # FIX: Added 'await' here
    result = await process_transfer_request(app_data)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result

@router.post("/transfer/verdict")
async def api_admin_verdict(data: TransferVerdictRequest):
    """Admin reviews and decides on the transfer request."""
    # FIX: Added 'await' here
    result = await process_manager_verdict(
        emp_id=data.emp_id, 
        verdict=data.verdict, 
        manager_notes=data.manager_notes
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result