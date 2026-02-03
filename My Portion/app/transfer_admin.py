import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from Agentics.planner_agents import meeting_planner

ATLAS_URI = os.getenv("MONGO_URI")

# Async Mongo Client
client = AsyncIOMotorClient(ATLAS_URI)
db = client["hr_database"]
requests_coll = db["transfer_requests"]
employee_coll = db["employee_portal"]


async def process_manager_verdict(emp_id: str, verdict: str, manager_notes: str):
    """
    Finalizes the transfer or triggers the meeting planner.
    """

    request = await requests_coll.find_one(
        {"emp_id": emp_id, "status": "pending"}
    )
    if not request:
        return {
            "status": "error",
            "message": "No pending request found for this ID."
        }

    verdict = verdict.lower()
    portal_coll = db["employee_portal"]

    if verdict == "approve":
        await portal_coll.update_one(
            {"emp_id": emp_id},
            {"$set": {"notification": "Transfer Approved"}}
        )

        await requests_coll.delete_one({"_id": request["_id"]})

        return {
            "status": "finalized",
            "message": "Transfer approved and record cleared."
        }

    elif verdict == "reject":
        await portal_coll.update_one(
            {"emp_id": emp_id},
            {"$set": {
                "notification": f"Transfer Rejected: {manager_notes}"
            }}
        )

        await requests_coll.delete_one({"_id": request["_id"]})

        return {
            "status": "finalized",
            "message": "Transfer rejected and record cleared."
        }

    elif verdict == "schedule_meeting":

        # Kept synchronous intentionally
        planner_state = meeting_planner({
            "emp_id": emp_id,
            "task": "transfer",
            "description": f"Transfer meeting of employee {emp_id}"
        })

        await requests_coll.update_one(
            {"emp_id": emp_id},
            {"$set": {"status": "meeting_in_progress"}}
        )

        return {
            "status": "meeting_initiated",
            "proposed_slots": planner_state["planner_outcome"].proposed_slots,
            "meeting_agenda": planner_state["planner_outcome"].meeting_agenda
        }

    return {
        "status": "error",
        "message": "Invalid verdict provided."
    }
