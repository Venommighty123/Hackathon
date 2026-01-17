from fastapi import APIRouter, HTTPException
# Fix: Importing from the Agentics folder at root
from Agentics import run_progress_workflow, StartRequest, SelectSlotRequest, QueryRequest, graph_app

router = APIRouter()

def make_initial_state(emp_id: str, task: str, description: str = ""):
    return {
        "emp_id": emp_id, "task": task, "description": description,
        "planner_outcome": None, "selected_slot": None, "final_status": None
    }

@router.post("/generate-progress-report")
async def generate_report(request: QueryRequest):
    try:
        return {"status": "success", "progress_report": await run_progress_workflow(request.user_query)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initiate")
async def initiate_meeting(req: StartRequest):
    config = {"configurable": {"thread_id": req.emp_id}}
    initial_state = make_initial_state(req.emp_id, req.task, req.description)
    await graph_app.ainvoke(initial_state, config=config)
    state = graph_app.get_state(config)
    return {
        "thread_id": req.emp_id,
        "options": state.values["planner_outcome"].proposed_slots,
        "agenda": state.values["planner_outcome"].meeting_agenda
    }

@router.post("/confirm")
async def confirm_meeting(req: SelectSlotRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    graph_app.update_state(config, {"selected_slot": req.selected_slot})
    await graph_app.ainvoke(None, config=config)
    final_state = graph_app.get_state(config)
    return {"status": final_state.values.get("final_status")}