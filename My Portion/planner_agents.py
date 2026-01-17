import os
import asyncio
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from datetime import datetime

from .app.state import AgentState_2
from .app.planner import planner_agent_node, human_approval_node

load_dotenv()

workflow = StateGraph(AgentState_2)

workflow.add_node("planner_agent", planner_agent_node)
workflow.add_node("manager_choice", human_approval_node)

workflow.set_entry_point("planner_agent")
workflow.add_edge("planner_agent", "manager_choice")
workflow.add_edge("manager_choice", END)

memory = MemorySaver()
graph_app = workflow.compile(
    checkpointer=memory,
    interrupt_before=["manager_choice"]
)

async def _meeting_planner_async(task: str, thread_id: str = "default_thread"):
    """
    Async execution of the LangGraph workflow.
    """
    initial_state = {"task": task}
    config = {"configurable": {"thread_id": thread_id}}

    final_state = await graph_app.ainvoke(
        initial_state,
        config=config
    )
    return final_state

def meeting_planner(task: str, thread_id: str = "default_thread"):
    """
    Executes the LangGraph workflow for a given user query.

    NOTE:
    This wrapper preserves synchronous behavior for existing callers
    while running the graph asynchronously under the hood.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():

        return loop.create_task(
            _meeting_planner_async(task, thread_id)
        )
    else:
        return asyncio.run(
            _meeting_planner_async(task, thread_id)
        )
