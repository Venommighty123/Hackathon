from fastapi import FastAPI
from app_rec.api.routes import router

app = FastAPI(
    title="AI Recruitment Agent",
    description="Automated Hiring Pipeline using LangGraph & MongoDB",
    version="1.0"
)

app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Recruitment AI System is Online & Ready."}