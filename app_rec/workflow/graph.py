from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app_rec.models.state import CandidateState
from app_rec.workflow.nodes import (
    check_eligibility, 
    score_candidate, 
    generate_rejection_email
)

# 1. Routing Logic
def route_eligibility(state: CandidateState):
    if state.get('is_eligible'):
        return "score_candidate"
    else:
        return "generate_rejection_email"

# 2. Build Graph
workflow = StateGraph(CandidateState)

# Nodes
workflow.add_node("check_eligibility", check_eligibility)
workflow.add_node("score_candidate", score_candidate)
workflow.add_node("generate_rejection_email", generate_rejection_email)

# Edges
workflow.set_entry_point("check_eligibility")

workflow.add_conditional_edges(
    "check_eligibility",
    route_eligibility,
    {
        "score_candidate": "score_candidate",
        "generate_rejection_email": "generate_rejection_email"
    }
)

workflow.add_edge("score_candidate", END)
workflow.add_edge("generate_rejection_email", END)

# 3. Compile with Checkpointer (Enables HITL capabilities later)
# We use MemorySaver for now. In production, you might use PostgresSaver.
checkpointer = MemorySaver()
candidate_flow_app = workflow.compile(checkpointer=checkpointer)