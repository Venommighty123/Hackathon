import os
import pytz
from .state import AgentState_2
from motor.motor_asyncio import AsyncIOMotorClient
from langchain_groq import ChatGroq
from .schemas import PlannerOutcome
from langchain_core.output_parsers import PydanticOutputParser
from Agentics.services.calendar_service import schedule_meeting, fetch_slots
from datetime import datetime
from langchain_core.messages import HumanMessage, ToolMessage

MONGO_URI = os.getenv("MONGO_URI")

client = AsyncIOMotorClient(MONGO_URI)
db = client["hr_database"]
complaints_col = db["complaints_log"]


async def planner_agent_node(state: AgentState_2):
    parser = PydanticOutputParser(pydantic_object=PlannerOutcome)
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    llm_with_fetch = llm.bind_tools([fetch_slots])

    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)

    prompt_text = f"""
        You are the HR Scheduling Specialist.
        Current IST Time: {now_ist.strftime('%I:%M %p')} on {now_ist.strftime('%Y-%m-%d')}
        Employee ID: {state['emp_id']}
        Subject: {state['task']}
        Description: {state['description']}

        CONSTRAINTS:
        1. Suggest EXACTLY 4 distinct timeslots between 09:00 AM and 05:00 PM IST.
        2. Use 'fetch_slots' for today and the next working day to ensure availability.
        3. Ensure a MINIMUM 2-hour gap between each suggested slot.
        4. Do NOT book anything. Only provide the options.

        {parser.get_format_instructions()}
    """

    messages = [HumanMessage(content=prompt_text)]

    for _ in range(2):
        response = llm_with_fetch.invoke(messages)
        if not response.tool_calls:
            break

        messages.append(response)

        for tool_call in response.tool_calls:
            result = fetch_slots.invoke(tool_call["args"])
            messages.append(
                ToolMessage(
                    tool_call_id=tool_call["id"],
                    content=str(result)
                )
            )

    final_res = llm.invoke(
        messages + [HumanMessage(content="Provide the 4 structured slots now.")]
    )

    return {
        "planner_outcome": parser.parse(final_res.content)
    }


async def human_approval_node(state: AgentState_2):
    slot = state.get("selected_slot")
    if not slot:
        return {"final_status": "Error: No slot selected."}

    parts = slot.split(" ")
    date_val = parts[0]
    time_val = " ".join(parts[1:])

    result = schedule_meeting.invoke({
        "emp_id": state["emp_id"],
        "date": date_val,
        "time_slot": time_val,
        "topic": state["planner_outcome"].meeting_agenda
    })

    if result.get("status") == "success":
        await complaints_col.delete_one(
            {"emp_id": str(state["emp_id"])}
        )
        return {
            "final_status": f"Meeting Booked: {result['link']}"
        }

    return {"final_status": "Failed to book meeting."}
