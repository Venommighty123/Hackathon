import os
import re
import json
from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from .state import AgentState_1
from .schemas import SynthesizerOutput


async def synthesizer_node(state: AgentState_1):
    """
    Synthesizer with Output Cleaning.
    Strips <think> tags and markdown before parsing JSON.
    """

    parser = PydanticOutputParser(pydantic_object=SynthesizerOutput)

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

    prompt = PromptTemplate(
        template="""
        You are a Senior HR Data Analyst. 
        Analyze the logs and return a strictly formatted JSON response.
        
        {format_instructions}
        
        DATA TO ANALYZE:
        {employee_data}
        
        CRITICAL RULES:
        1. Output ONLY the raw JSON. 
        2. DO NOT include <think> tags. 
        3. DO NOT include introductory text or markdown code blocks.
        4. Ensure all lists (days, task_scores, etc.) have matching lengths.
        """,
        input_variables=["employee_data"],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
        }
    )

    chain = prompt | llm

    try:
        # LangChain invoke kept synchronous
        response = chain.invoke({
            "employee_data": state["employee_data"]
        })

        raw_content = response.content

        if "<think>" in raw_content:
            raw_content = raw_content.split("</think>")[-1].strip()

        raw_content = re.sub(
            r"```json\s*|```",
            "",
            raw_content
        ).strip()

        structured_data = parser.parse(raw_content)

        return {
            "summary_data": structured_data
        }

    except Exception as e:
        print(
            "[!] Parsing failed even after cleaning. "
            f"Raw response was: {response.content[:200]}..."
        )
        return {
            "summary_data": None
        }
