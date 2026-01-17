import re
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

# Local imports
from .schemas import AdminOutcome, TransferApplication
from .retriever import MongoDBHRPipeline

ATLAS_URI = "mongodb+srv://mathurkushagra163_db_user:ElTitz0clXuFXUeu@cluster0.1c2z3gd.mongodb.net/?appName=Cluster0"

# Async Mongo Client
client = AsyncIOMotorClient(ATLAS_URI)
db = client["hr_database"]
requests_coll = db["transfer_requests"]

async def process_transfer_request(application_data: TransferApplication):
    """
    Validates transfer request, checks for existing pending requests,
    and updates the transfer_requests collection using a strict policy framework.
    """
    emp_id = application_data.emp_id

    # 1. Existing request check
    existing_request = await requests_coll.find_one(
        {"emp_id": emp_id, "status": "pending"}
    )
    if existing_request:
        return {
            "status": "exists",
            "message": "Your transfer request has been sent, please wait for admin approval."
        }

    # 2. Initialization
    parser = PydanticOutputParser(pydantic_object=AdminOutcome)
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

    # 3. Policy Retrieval
    mongo_pipe = MongoDBHRPipeline(connection_string=ATLAS_URI)
    query_text = (
        f"{application_data.transfer_type} "
        f"from {application_data.current_zone} "
        f"to {application_data.desired_zone}. "
        f"Reason: {application_data.reason}. "
        f"Additional Details: {application_data.additional_details or 'None'}."
    )
    context_policies = mongo_pipe.fetch_top_policies(query_text)

    # 4. Structured Prompt Template
    prompt = PromptTemplate(
        template="""
            You are a Senior HR Data Analyst operating in STRICT JSON MODE.

            Your task is to analyze the provided employee performance logs and return
            a response that EXACTLY matches the JSON schema named **SynthesizerOutput**.

            {format_instructions}

            ========================
            DATA TO ANALYZE:
            ========================
            {employee_data}

            ========================
            NON-NEGOTIABLE OUTPUT RULES:
            ========================
            1. Output MUST be a single, valid JSON object conforming EXACTLY to SynthesizerOutput.
            2. Output MUST contain ALL required fields — no missing, null, or extra keys.
            3. Output MUST NOT contain:
                - Explanatory text
                - Markdown
                - Code fences
                - XML or <think> tags
            4. JSON keys MUST match schema names EXACTLY (case-sensitive).
            5. All numeric fields MUST be valid numbers (no strings, NaN, or null).
            6. Lists `days`, `task_scores`, `attendance_pcts`, and `screen_time_hours`
            MUST:
                - Have identical lengths
                - Represent the same ordered sequence of days
            7. Constraints:
                - burnout_risk MUST be an integer between 1 and 10
                - productivity_index MUST be a float between 0 and 100
            8. The `analysis` field MUST be a SINGLE string containing EXACTLY 3 paragraphs:
                - Paragraph 1: Performance trends
                - Paragraph 2: Risks or concerns
                - Paragraph 3: Actionable recommendations
            9. If ANY rule is violated, the output is considered INVALID.

            Before finalizing your response:
                - Internally verify schema compliance
                - Fix any violations
                - THEN output the JSON

            FINAL OUTPUT:
            Return ONLY the raw JSON object. Nothing else.
            """,
        input_variables=["employee_data"],
        partial_variables={
        "format_instructions": parser.get_format_instructions()
        }
    )

    try:
        chain = prompt | llm
        response = chain.invoke({
            "context": context_policies,
            "application": application_data.model_dump()
        })

        # Cleaning logic
        raw_content = (
            re.sub(r"```json\s*|```", "", response.content)
            .split("</think>")[-1]
            .strip()
        )

        outcome = parser.parse(raw_content)

        # 6. Result Logic (Using is_valid and status matching)
        if outcome.status == "true":
            await requests_coll.insert_one({
                "emp_id": emp_id,
                "application": application_data.model_dump(),
                "status": "pending",
                "ai_reasoning": outcome.reasoning,
                "created_at": datetime.now()
            })

            return {
                "status": "success",
                "message": "Request submitted for Admin review."
            }

        return {
            "status": "rejected",
            "message": f"Policy Violation: {outcome.reasoning}"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"System Failure: {str(e)}"
        }