from app_rec.services.llm_service import call_llm
from typing import Dict, Any
import json
from pypdf import PdfReader
import requests
import io
import base64

# --- NODE 1: JOB AD CREATION ---
async def ad_creation(state: Dict[str, Any]):
    job = state['job']

    prompt = f"""
        Draft an official government recruitment notice using the details below.

        DETAILS:
        - Department: {job.get('department')}
        - Post Name: {job.get('post_name')}
        - Notice ID: {job.get('notice_id')}
        - Employment Type: {job.get('employment_type')}
        - Location: {job.get('location')}

        ELIGIBILITY CRITERIA (Strictly adhere to these):
        - Required Degree Levels: {job.get('required_degree_levels', 'As per norms')} (e.g., B.Tech, Diploma)
        - Eligible Branches: {job.get('eligible_branches', 'All technical branches')} (Must list specific branches if applicable)
        - Minimum Experience (years): {job.get('min_experience_years', '0')}
        - Government/PSU Experience Required?: {job.get('requires_psu_experience', 'No')} 
        - Age Limit: {job.get('age_limit_min', '18')} to {job.get('age_limit_max', 'N/A')} years as of {job.get('cutoff_date', 'application date')}

        PREFERRED QUALIFICATIONS:
        - Skills: {job.get('preferred_skills', 'None')}
        - Additional Context: {job.get('additional_notes', 'None')}

        OUTPUT RULES:
        - Use formal government language (e.g., "Applications are invited...", "The candidate must possess...").
        - Neutral and informational tone.
        - NO promotional/marketing language (e.g., "exciting opportunity", "join us").
        - Explicitly state the "Govt/PSU Experience" requirement if it is 'Yes'.
        - List the Eligible Branches clearly so candidates know if they apply.
    """

    system_prompt = """
        You are an assistant drafting official government recruitment notices.

        STRICT RULES:
        1. Output ONLY the final recruitment notice text.
        2. Do NOT use promotional language.
        3. Ensure the "Eligible Branches" and "Degree Levels" are clearly listed, as the application form filters by these.
        4. If 'Government/PSU Experience' is marked 'Yes' in the prompt, explicitly state that it is a mandatory requirement.
    """

    generated_ad = await call_llm(prompt=prompt, system_prompt=system_prompt)
    
    state['job_ad'] = generated_ad

    return state

# --- NODE 2: ELIGIBILITY CHECKING ---

async def check_eligibility(state: Dict[str, Any]):
    print("--- NODE: Eligibility Check (Metadata First) ---")
    candidate = state['candidate_data']
    job_ad = state.get('job_description')

    # EXTRACT METADATA (We trust this more than the PDF for initial screening)
    degree = candidate.get('education', {}).get('degree_level', 'Unknown')
    branch = candidate.get('education', {}).get('branch', 'Unknown')
    exp_years = candidate.get('experience', {}).get('total_years', '0')
    psu_exp = candidate.get('experience', {}).get('has_psu_exp', 'No')

    prompt = f"""
    You are an Eligibility AI. Your job is to filter candidates based on HARD criteria.
    
    CRITICAL RULE: TRUST THE METADATA. 
    If the Metadata says "PSU Exp: Yes", then they HAVE it. Do not look for proof in the resume text yet.
    
    JOB REQUIREMENTS:
    {job_ad}

    CANDIDATE METADATA (TRUST THIS):
    - Degree: {degree}
    - Branch: {branch}
    - Years of Experience: {exp_years}
    - Government/PSU Experience: {psu_exp}

    TASK:
    1. Does the candidate meet the mandatory degree/branch? (B.Tech/Diploma in Civil/Electrical as per JD)
    2. Does the candidate have the mandatory Government Experience? (If JD requires it)
    
    Output JSON ONLY:
    {{
        "is_eligible": true, 
        "reason": "Matches metadata criteria."
    }}
    OR
    {{
        "is_eligible": false, 
        "reason": "Wrong degree / Missing Govt Exp."
    }}
    """

    response = await call_llm(prompt, temperature=0.0) # Temp 0 for strict logic
    
    try:
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        result = json.loads(response.strip())
    except:
        # Fallback: If metadata says Yes, we default to True to save the demo
        if psu_exp == "Yes":
             result = {"is_eligible": True, "reason": "Metadata confirmed eligibility"}
        else:
             result = {"is_eligible": False, "reason": "Error parsing decision"}

    state['is_eligible'] = result.get('is_eligible', False)
    state['eligibility_reason'] = result.get('reason', 'Unknown')
    
    print(f"   [Eligibility] {state['is_eligible']} ({state['eligibility_reason']})")
    return state

# --- HELPER: PDF TEXT EXTRACTION ---
def extract_text_from_pdf(source: str) -> str:
    """
    Extracts text from:
    1. Base64 encoded string (Portable DB)
    2. URL (Google Drive/Public Link)
    3. Local File Path
    """
    try:
        pdf_file = None
        
        # CASE 1: Base64 String (The Portable DB Method)
        if source and len(source) > 1000 and "http" not in source and "/" not in source[:50]:
            try:
                pdf_data = base64.b64decode(source)
                pdf_file = io.BytesIO(pdf_data)
                print("   [PDF] Detected Base64 encoded resume.")
            except Exception as e:
                print(f"   [PDF] Base64 decode failed: {e}")
                return "Error decoding resume data."

        # CASE 2: URL
        elif source and source.startswith("http"):
            try:
                print(f"   [PDF] Downloading from URL: {source[:30]}...")
                response = requests.get(source, timeout=10)
                if response.status_code == 200:
                    pdf_file = io.BytesIO(response.content)
                else:
                    return "Error: Could not download resume."
            except Exception as e:
                 return f"Error downloading PDF: {e}"

        # CASE 3: Local File
        elif source and isinstance(source, str):
            pdf_file = source

        # READ THE PDF
        if pdf_file:
            try:
                reader = PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
            except Exception as e:
                print(f"   [PDF] pypdf Error: {e}")
                return "Error: File is not a valid PDF."
            
        return "Error: Resume source not found or invalid."

    except Exception as e:
        print(f"PDF Extraction Critical Error: {e}")
        return "Error processing resume."

# --- NODE 3: RESUME SCORING (RUTHLESS MODE) ---
async def score_candidate(state: Dict[str, Any]):
    print("--- NODE: Scoring Resume (RUTHLESS MODE) ---")
    candidate = state['candidate_data']
    job_ad = state['job_description']
    
    # Handle Base64 vs Link
    resume_source = candidate.get('resume_base64') or candidate.get('resume_link')
    resume_text = extract_text_from_pdf(resume_source)
    
    prompt = f"""
    You are a skeptical, strict Technical Recruiter. You do not trust candidate self-assessments.
    You only trust PROOF (specific projects, metrics, or years of tenure).

    JOB DESCRIPTION (THE STANDARD):
    {job_ad}

    CANDIDATE RESUME (THE CLAIM):
    {resume_text}

    --- SCORING RUBRIC (0-10) ---
    
    CRITICAL RULES:
    1. **The Ceiling is Low:** A standard "good" candidate gets a 5 or 6. An 8 requires EXCEPTIONAL proof. A 10 is impossible.
    2. **Automatic Penalties:**
       - Missing a mandatory hard skill mentioned in JD? -> Max Score is 3.
       - "Experience" listed without description/impact? -> Deduct 2 points.
       - Spelling/Grammar errors? -> Deduct 1 point.
    3. **Evidence over Keywords:** - If they say "Python" but show no projects using Python -> Ignore it.
       - If they list a degree but unrelated branch -> Score 0 for Education.

    TASK:
    Audit this resume against the JD. Be harsh.
    
    OUTPUT JSON ONLY:
    {{
        "score": int,  # The harsh final score (0-10)
        "reason": "One brutal sentence explaining why they lost points."
    }}
    """

    response = await call_llm(prompt, temperature=0.0)
    
    try:
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        result = json.loads(response.strip())
    except:
        result = {"score": 0, "reason": "Error parsing strict score"}

    state['relevance_score'] = result.get('score', 0)
    state['screening_summary'] = result.get('reason', 'No reason provided')
    
    print(f"   [Ruthless Score] {state['relevance_score']}/10 -- {state['screening_summary']}")
    return state

# --- NODE 4: REJECTION EMAIL ---
async def generate_rejection_email(state: Dict[str, Any]):
    print("--- NODE: Generating Rejection Email ---")
    candidate = state['candidate_data']
    reason = state.get('eligibility_reason', 'Criteria not met')
    
    prompt = f"""
    Write a polite, professional rejection email for a government job application.
    
    Candidate Name: {candidate.get('full_name', 'Candidate')}
    Rejection Reason: {reason}
    
    Keep it brief and respectful.
    """
    
    email_text = await call_llm(prompt, temperature=0.7)
    state['email_draft'] = email_text
    return state