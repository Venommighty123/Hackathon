import os
import asyncio
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from datetime import datetime

from .app import (
    AgentState_1,
    retriever_node,
    synthesizer_node
)

load_dotenv()

workflow = StateGraph(AgentState_1)

workflow.add_node("retrieve", retriever_node)
workflow.add_node("synthesize", synthesizer_node)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "synthesize")
workflow.add_edge("synthesize", END)

memory = MemorySaver()
progress_tracking_app = workflow.compile(checkpointer=memory)

async def _run_progress_workflow_async(
    user_query: str,
    thread_id: str = "default_thread"
):
    """
    Async execution of the LangGraph workflow.
    """
    initial_state = {"user_query": user_query}
    config = {"configurable": {"thread_id": thread_id}}

    final_state = await progress_tracking_app.ainvoke(
        initial_state,
        config=config
    )
    return final_state

async def run_progress_workflow(
    user_query: str,
    thread_id: str = "default_thread"
):
    initial_state = {
        "user_query": user_query,
        "emp_id": None,
        "employee_data": "",
        "summary_data": None
    }

    config = {"configurable": {"thread_id": thread_id}}

    return await progress_tracking_app.ainvoke(
        initial_state,
        config=config
    )

