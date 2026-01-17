from typing import TypedDict, Optional
from .schemas import SynthesizerOutput, PlannerOutcome

class AgentState_1(TypedDict):
    emp_id: str
    user_query: str
    employee_data: str
    summary_data: Optional[SynthesizerOutput]

class AgentState_2(TypedDict):
    emp_id: str
    task: str
    description: str
    planner_outcome: Optional[PlannerOutcome]
    selected_slot: Optional[str]
    final_status: Optional[str]