# app/database/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class DatabaseRepository(ABC):
    
    # --- JOB OPERATIONS ---
    @abstractmethod
    async def create_job_posting(self, title: str, description: str, form_link: str) -> str:
        pass

    @abstractmethod
    async def get_job_details(self, job_id: str) -> Dict[str, Any]:
        pass

    # --- CANDIDATE OPERATIONS ---
    @abstractmethod
    async def add_candidate(self, job_id: str, candidate_data: Dict[str, Any]) -> str:
        """
        candidate_data should match the Google Form fields:
        {
            "full_name": str,
            "email": str,
            "dob": str,
            "contact_number": str,
            "education": {
                "degree_level": str, # Diploma, B.Tech, etc.
                "branch": str,       # CSE, IT, etc.
                "status": str,       # Final Year, Completed
                "graduation_year": str,
                "institution": str
            },
            "experience": {
                "total_years": str,
                "has_psu_exp": bool, # Yes/No
                "description": str   # Brief description
            },
            "resume_link": str,      # Google Drive link from form
            "declaration": bool
        }
        """
        pass

    @abstractmethod
    async def get_candidate(self, candidate_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def update_candidate_status(self, candidate_id: str, status: str, ai_notes: Optional[str] = None) -> bool:
        pass