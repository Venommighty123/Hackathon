import os
import warnings
import uvicorn
from fastapi import FastAPI

# Silence warnings before heavy imports
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 

# Import Routers - Use the folder names exactly as they appear in your sidebar
from app_rec.api.routes import router as recruitment_router
from api.attendance import router as attendance_router
from api.grievance import router as grievance_router
from api.meeting import router as meeting_router

app = FastAPI(
    title="Unified AI HR System",
    description="Recruitment + Employee Management + Attendance",
    version="2.0"
)

# Include Routers
app.include_router(recruitment_router, prefix="/recruitment", tags=["Recruitment"])
app.include_router(attendance_router, prefix="/attendance", tags=["Attendance"])
app.include_router(grievance_router, prefix="/grievance", tags=["Grievance"])
app.include_router(meeting_router, prefix="/meeting", tags=["Meeting"])

@app.get("/")
async def root():
    return {"message": "All AI Systems Online."}

if __name__ == "__main__":
    # Ensure you use the string "main:app" for reload to work correctly
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)