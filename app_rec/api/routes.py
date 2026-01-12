from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Dict, Any
import json
import ast
import random
import io
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from app_rec.database.mongo_db import DatabaseRepository, get_db
from app_rec.services.llm_service import call_llm, clean_json_response
from app_rec.workflow.graph import candidate_flow_app

router = APIRouter()

# --- HELPER: PDF GENERATION FOR SIMULATION ---
def generate_pdf_base64(name, education, experience, skills):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, f"RESUME: {name}")
    c.setFont("Helvetica", 11)
    c.drawString(50, 720, f"EDUCATION: {education}")
    c.drawString(50, 690, "EXPERIENCE:")
    text_obj = c.beginText(150, 690)
    for line in experience.split('\n'):
        text_obj.textLine(line)
    c.drawText(text_obj)
    c.drawString(50, 550, f"SKILLS: {skills}")
    c.save()
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')

# 1. PAGE 1: PUBLIC ANNOUNCEMENTS

@router.get("/jobs/announcements")
async def get_active_announcements(db: DatabaseRepository = Depends(get_db)):
    """Fetches 'OPEN' jobs for the Public Portal."""
    cursor = db.jobs.find({"status": "OPEN"})
    jobs = []
    async for job in cursor:
        jobs.append({
            "id": str(job["_id"]),
            "title": job.get("title"),
            "department": job.get("structured_data", {}).get("department", "MCD"),
            "summary": job.get("structured_data", {}).get("summary", ""),
            "form_link": "https://forms.google.com/demo-apply"
        })
    return jobs

# 2. PAGE 2: ADMIN JD CREATION

@router.post("/jobs/generate-draft")
async def generate_draft_job(input_data: dict, db: DatabaseRepository = Depends(get_db)):
    """Step 1: Admin types requirements -> AI creates Draft."""
    raw_text = input_data.get("raw_text", "")
    
    prompt = f"""
    Analyze this Hiring Manager Request and extract structured job details.
    Request: "{raw_text}"
    Output JSON keys: title, department, summary, responsibilities (list), requirements (list).
    """
    raw_response = await call_llm(prompt)
    structured_data = clean_json_response(raw_response)
    
    formatted_desc = f"""
    **Role:** {structured_data.get('title')}
    **Department:** {structured_data.get('department')}
    **Summary:** {structured_data.get('summary')}
    **Responsibilities:** {chr(10).join(['- '+r for r in structured_data.get('responsibilities', [])])}
    **Requirements:** {chr(10).join(['- '+r for r in structured_data.get('requirements', [])])}
    """
    
    job_id = await db.create_job({
        "title": structured_data.get('title'),
        "description": formatted_desc,
        "structured_data": structured_data,
        "raw_input": raw_text,
        "status": "DRAFT"
    })
    
    return {"message": "Draft Generated", "job_id": job_id, "structured_preview": structured_data}

@router.post("/jobs/{job_id}/approve")
async def approve_job(job_id: str, approval: dict, db: DatabaseRepository = Depends(get_db)):
    """Step 2: Admin Approves -> Job goes OPEN."""
    job = await db.get_job_details(job_id)
    if not job: raise HTTPException(status_code=404, detail="Job not found")

    if approval.get("approved"):
        await db.update_job_status(job_id, "OPEN")
        return {"message": "Job Published!", "status": "OPEN"}
    else:
        return {"message": "Feedback received (Implementation skipped for this specific demo step)"}

# 3. PAGE 2: SIMULATION & RESULTS (THE MAGIC)

@router.post("/simulation/run/{job_id}")
async def run_simulation(
    job_id: str, 
    background_tasks: BackgroundTasks,
    db: DatabaseRepository = Depends(get_db)
):
    """
    ONE-CLICK DEMO:
    1. Generates 50 Fake Candidates (Elite, Average, Spam).
    2. Injects them into DB linked to this Job ID.
    3. Triggers AI Analysis for all of them.
    """
    print(f"--- [Simulation] Starting Injection for Job {job_id} ---")
    
    FIRST_NAMES = ["Rajesh", "Amit", "Sunita", "Priya", "Vikram", "Rahul", "Karthik", "Sneha"]
    LAST_NAMES = ["Kumar", "Sharma", "Verma", "Singh", "Gupta", "Malik", "Nair", "Reddy"]
    
    candidates_batch = []

    # A. THE ELITE (Govt Exp + Great Resume)
    elite_exps = [
        "Senior Site Engineer at CPWD (3 years).\n- Managed highway construction.\n- Expert in AutoCAD & estimation.\n- Zero safety violations.",
        "Junior Engineer at DDA (4 years).\n- Supervised housing project.\n- Quality checks (ISO standards).\n- Proficient in Total Station."
    ]
    for i in range(5):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        pdf = generate_pdf_base64(name, "B.Tech Civil (DTU)", random.choice(elite_exps), "AutoCAD, StaadPro, CPWD Manuals")
        candidates_batch.append({
            "full_name": name, "status": "NEW", "job_id": job_id, "resume_base64": pdf,
            "education": {"degree_level": "B.Tech", "branch": "Civil Engineering"},
            "experience": {"has_psu_exp": "Yes", "total_years": "4", "description": "Govt Exp"}
        })

    # B. THE AVERAGE (Govt Exp + Generic Resume)
    for i in range(15):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        pdf = generate_pdf_base64(name, "Diploma Civil", "Contractual Engineer at MCD.\n- Road repair supervision.", "Site Supervision")
        candidates_batch.append({
            "full_name": name, "status": "NEW", "job_id": job_id, "resume_base64": pdf,
            "education": {"degree_level": "Diploma", "branch": "Civil Engineering"},
            "experience": {"has_psu_exp": "Yes", "total_years": "2", "description": "Govt Exp"}
        })

    # C. SPAM / REJECTED
    for i in range(15):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        pdf = generate_pdf_base64(name, "B.Com", "Sales Associate for 2 years.", "Excel, Word")
        candidates_batch.append({
            "full_name": name, "status": "NEW", "job_id": job_id, "resume_base64": pdf,
            "education": {"degree_level": "Other", "branch": "Other"},
            "experience": {"has_psu_exp": "No", "total_years": "1", "description": "Irrelevant"}
        })

    await db.candidates.insert_many(candidates_batch)
    
    new_candidates = await db.get_candidates_by_job(job_id)
    count = 0
    for cand in new_candidates:
        if cand.get('status') == "NEW":
            background_tasks.add_task(run_ai_pipeline, candidate_id=cand['id'], db=db)
            count += 1
            
    return {"message": f"Simulation started. Injected {len(candidates_batch)} candidates. AI Processing {count} candidates."}


@router.get("/jobs/{job_id}/dashboard-results")
async def get_dashboard_results(job_id: str, db: DatabaseRepository = Depends(get_db)):
    """
    Fetches the 'Magic' Lower Half: Stats, Top 5, and Interview Questions.
    """
    # 1. Stats & Ranking
    candidates = await db.get_candidates_by_job(job_id)
    eligible = [c for c in candidates if c.get('status') == "ELIGIBLE"]
    rejected = [c for c in candidates if c.get('status') == "REJECTED"]
    
    def get_score(cand):
        try:
            notes = cand.get('ai_notes', "{}")
            if isinstance(notes, str):
                import ast
                return int(ast.literal_eval(notes).get('score', 0))
            return 0
        except: return 0

    ranked = sorted(eligible, key=get_score, reverse=True)
    top_5 = ranked[:5]

    # 2. Generate Interview Questions (On the Fly if needed)
    questions = {}
    if top_5:
        job = await db.get_job_details(job_id)
        jd_text = job.get("description", "")
        prompt = f"""
        Based on JD: {jd_text[:200]}...
        Generate JSON: {{ "technical": ["Q1", "Q2"], "scenario": "Stress Test" }}
        """
        raw = await call_llm(prompt)
        questions = clean_json_response(raw)

    return {
        "stats": {
            "total_applicants": len(candidates),
            "selected": len(eligible),
            "rejected": len(rejected)
        },
        "top_candidates": [
            {
                "name": c['full_name'],
                "score": get_score(c),
                "education": c.get('education', {}).get('degree_level'),
                "summary": c.get('ai_notes', '')
            } for c in top_5
        ],
        "interview_guide": questions
    }

async def run_ai_pipeline(candidate_id: str, db: DatabaseRepository):
    try:
        candidate = await db.get_candidate(candidate_id)
        if not candidate: return
        job_id = candidate.get('job_id')
        job_record = await db.get_job_details(job_id)
        if not job_record: return
        
        jd_text = job_record.get('description', '')
        print(f"--- [Pipeline] Processing {candidate.get('full_name')} ---")

        initial_state = {
            "candidate_id": candidate_id, "candidate_data": candidate, "job_description": jd_text
        }
        config = {"configurable": {"thread_id": candidate_id}}
        final_state = await candidate_flow_app.ainvoke(initial_state, config=config)
        
        if final_state.get('is_eligible'):
            ai_data = {"score": final_state.get('relevance_score'), "summary": final_state.get('screening_summary')}
            await db.update_candidate_status(candidate_id, "ELIGIBLE", ai_notes=str(ai_data))
        else:
            reason = final_state.get('eligibility_reason')
            await db.update_candidate_status(candidate_id, "REJECTED", ai_notes=f"Reason: {reason}")
            
    except Exception as e:
        print(f"PIPELINE ERROR: {e}")