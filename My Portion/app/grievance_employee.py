from .retriever import MongoDBHRPipeline
import re
import os
from .schemas import GrievanceApplication, CheckingOutcome
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

MONGO_URI = "mongodb+srv://mathurkushagra163_db_user:ElTitz0clXuFXUeu@cluster0.1c2z3gd.mongodb.net/?appName=Cluster0"

# Async Mongo Client
client = AsyncIOMotorClient(MONGO_URI)
db = client["hr_database"]
complaints_col = db["complaints_log"]


async def process_complaints(app_data: GrievanceApplication):
    emp_id = app_data.emp_id

    # Async check for existing pending grievance
    existing = await complaints_col.find_one(
        {"emp_id": emp_id, "status": "pending"}
    )
    if existing:
        return {
            "status": "exists",
            "message": "A pending grievance is already being processed."
        }

    parser = PydanticOutputParser(pydantic_object=CheckingOutcome)
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

    # Kept synchronous (logic preserved)
    mongo_pipe = MongoDBHRPipeline(connection_string=MONGO_URI)
    query_text = f"{app_data.grievance_type}: {app_data.subject}"
    context_policies = mongo_pipe.fetch_top_policies(query_text)

    prompt = PromptTemplate(
        template="""
        ROLE:
        You are a strict HR Policy Compliance Auditor specialized in Grievance & Complaint evaluation.

        OBJECTIVE:
        Evaluate the employee APPLICATION strictly against the POLICY CONTEXT.
        Your task is NOT to be empathetic or suggest solutions.
        Your task is to decide POLICY COMPLIANCE ONLY.

        OUTPUT RULES (MANDATORY):
            - Respond ONLY in the JSON format specified below.
            - Do NOT add extra keys.
            - Do NOT include markdown, explanations, or commentary outside JSON.
            - Reasoning MUST explicitly cite one or more HR-POL codes.

        {format_instructions}

        DECISION FRAMEWORK:
        Apply the rules in the exact order listed.

            1. SCOPE CHECK (HR-POL-72.2)
                - If the grievance requests or implies promotion, role change, or transfer → INVALID.

            2. REDUNDANCY CHECK (HR-POL-13.3)
                - If the grievance repeats a previously filed or resolved promotion-related complaint → INVALID.

            3. ACCESS & PERFORMANCE CHECK (HR-POL-12.2)
                - If the employee is under PIP OR
                - If screen time dropped by more than 40% in the last monitoring window
                - Access limitation or grievance rejection is JUSTIFIED.

            4. FINAL VERDICT
                - If NONE of the above violations apply → VALID.
                - Otherwise → INVALID.

        INPUT DATA:
        POLICY CONTEXT:
        {context}

        EMPLOYEE APPLICATION:
        {application}
        """,
        input_variables=["context", "application"],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
        }
    )

    try:
        chain = prompt | llm

        # LangChain invoke kept synchronous
        response = chain.invoke({
            "context": context_policies,
            "application": app_data.model_dump()
        })

        content = (
            re.sub(r"```json\s*|```", "", response.content)
            .split("</think>")[-1]
            .strip()
        )

        outcome = parser.parse(content)

        if outcome.is_valid:
            await complaints_col.insert_one({
                "emp_id": emp_id,
                "application": app_data.model_dump(),
                "status": "pending",
                "report_date": datetime.now(),
                "ai_reasoning": outcome.reasoning
            })

            return {
                "status": "success",
                "message": "Grievance submitted for review."
            }

        return {
            "status": "rejected",
            "message": f"Policy Rejection: {outcome.reasoning}"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Verification failed: {str(e)}"
        }
