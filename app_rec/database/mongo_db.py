import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseRepository:
    """
    Abstract Interface for Database (Optional, but good practice).
    We define the structure here, but the logic is in MongoDB class below.
    """
    pass

class MongoDB(DatabaseRepository):
    def __init__(self):
        self.uri = os.getenv("MONGO_URI")
        self.db_name = "recruitment_db"
        self.client = AsyncIOMotorClient(self.uri, tlsAllowInvalidCertificates=True)
        self.db = self.client[self.db_name]
        
        # Collections
        self.jobs = self.db.jobs
        self.candidates = self.db.candidates

    # ==========================================
    # JOB OPERATIONS
    # ==========================================

    async def create_job(self, job_data: Dict[str, Any]) -> str:
        """Creates a new Job Posting (Draft or Open)."""
        result = await self.jobs.insert_one(job_data)
        return str(result.inserted_id)

    async def get_job_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetches job details. Converts ObjectId to string for LangGraph safety."""
        try:
            if not ObjectId.is_valid(job_id):
                return None
                
            job = await self.jobs.find_one({"_id": ObjectId(job_id)})
            if job:
                job["id"] = str(job["_id"])  # Add string ID
                del job["_id"]               # DELETE ObjectId (Fixes LangGraph Crash)
                return job
            return None
        except Exception as e:
            print(f"Error fetching job {job_id}: {e}")
            return None

    async def update_job_status(self, job_id: str, status: str):
        """Updates job status (e.g., DRAFT -> OPEN)."""
        if ObjectId.is_valid(job_id):
            await self.jobs.update_one(
                {"_id": ObjectId(job_id)},
                {"$set": {"status": status}}
            )

    async def update_job_draft(self, job_id: str, new_description: str):
        """Updates the description of a Draft Job (Used in HITL flow)."""
        try:
            if ObjectId.is_valid(job_id):
                await self.jobs.update_one(
                    {"_id": ObjectId(job_id)},
                    {"$set": {"description": new_description}}
                )
                return True
            return False
        except Exception as e:
            print(f"Error updating draft: {e}")
            return False

    # ==========================================
    # CANDIDATE OPERATIONS
    # ==========================================

    async def create_candidate(self, candidate_data: Dict[str, Any]) -> str:
        """Adds a new candidate application."""
        result = await self.candidates.insert_one(candidate_data)
        return str(result.inserted_id)

    async def get_candidate(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a single candidate. Sanitizes ObjectId."""
        try:
            if not ObjectId.is_valid(candidate_id):
                return None

            cand = await self.candidates.find_one({"_id": ObjectId(candidate_id)})
            if cand:
                cand["id"] = str(cand["_id"])
                del cand["_id"]  # DELETE ObjectId (Fixes LangGraph Crash)
                return cand
            return None
        except Exception as e:
            print(f"Error fetching candidate {candidate_id}: {e}")
            return None

    async def get_candidates_by_job(self, job_id: str) -> List[Dict[str, Any]]:
        """Fetches all candidates for a specific job."""
        cursor = self.candidates.find({"job_id": job_id})
        candidates = []
        async for doc in cursor:
            doc["id"] = str(doc["_id"])
            del doc["_id"]  # DELETE ObjectId
            candidates.append(doc)
        return candidates

    async def update_candidate_status(self, candidate_id: str, status: str, ai_notes: str = None):
        """Updates candidate status and saves AI scoring/summary."""
        update_data = {"status": status}
        if ai_notes:
            update_data["ai_notes"] = ai_notes

        if ObjectId.is_valid(candidate_id):
            await self.candidates.update_one(
                {"_id": ObjectId(candidate_id)},
                {"$set": update_data}
            )

# Dependency Injection Helper
db_instance = MongoDB()

def get_db() -> DatabaseRepository:
    return db_instance