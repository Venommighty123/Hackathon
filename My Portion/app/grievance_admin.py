import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from Agentics.planner_agents import meeting_planner
from dotenv import load_dotenv

load_dotenv()
ATLAS_URI = os.getenv("MONGO_URI")
# Async Mongo Client
client = AsyncIOMotorClient(ATLAS_URI)
db = client["hr_database"]
complaints_col = db["complaints_log"]
employee_coll = db["employee_portal"]


async def process_grievance_verdict(emp_id: str, verdict: str, manager_notes: str):
    # Async find
    request = await complaints_col.find_one(
        {"emp_id": emp_id, "status": "pending"}
    )

    if not request:
        return {
            "status": "error",
            "message": "Grievance not found or already processed."
        }

    verdict = verdict.lower()
    portal = db["employee_portal"]

    if verdict == "approve":
        await portal.update_one(
            {"emp_id": emp_id},
            {"$set": {
                "portal_notification": "Complaint Approved: Passed to upper departments."
            }}
        )

        await complaints_col.delete_one({"_id": request["_id"]})

        return {
            "status": "finalized",
            "message": "Grievance approved."
        }

    elif verdict == "reject":
        await portal.update_one(
            {"emp_id": emp_id},
            {"$set": {
                "portal_notification": f"Complaint Rejected: {manager_notes}"
            }}
        )

        await complaints_col.delete_one({"_id": request["_id"]})

        return {
            "status": "finalized",
            "message": "Grievance rejected."
        }

    elif verdict == "schedule_meeting":
        task_desc = (
            f"Grievance Discussion: "
            f"{request['application']['Subject']} - "
            f"{request['application']['Description']}"
        )

        # Kept synchronous intentionally (logic preserved)
        planner_res = meeting_planner(
            task=task_desc,
            thread_id=f"grievance_{emp_id}"
        )

        await complaints_col.update_one(
            {"emp_id": emp_id},
            {"$set": {"status": "meeting_scheduled"}}
        )

        return {
            "status": "meeting_initiated",
            "proposed_slots": planner_res["planner_outcome"].proposed_slots,
            "agenda": planner_res["planner_outcome"].meeting_agenda
        }

    return {
        "status": "error",
        "message": "Invalid verdict."
    }
