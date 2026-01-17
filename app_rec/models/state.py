# app/models/state.py
from typing import TypedDict, Optional, List, Dict, Any

# total=False means "It's okay if some keys are missing at the start"
class CandidateState(TypedDict, total=False): 
    """
    Represents the state of a candidate as they move through the graph.
    """
    # 1. Core Data (From Database)
    candidate_id: str
    job_id: str
    candidate_data: Dict[str, Any] # The full form data
    job_description: str           # The text to match against
    
    # 2. Pipeline Progress (AI Outputs)
    # Eligibility Check
    is_eligible: Optional[bool] 
    eligibility_reason: Optional[str]
    
    # Resume Screening
    relevance_score: Optional[int] # 0-100
    screening_summary: Optional[str]
    
    # Outreach
    email_draft: Optional[str]