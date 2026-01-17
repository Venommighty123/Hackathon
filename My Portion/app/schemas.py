from pydantic import BaseModel, Field
from typing import List, Optional

class QueryRequest(BaseModel):
    user_query: str

class PerformanceMetrics(BaseModel):
    days: List[str] = Field(description="The days of the week (e.g., Mon, Tue, etc.)")
    task_scores: List[float] = Field(description="List of task completion scores for each day")
    attendance_pcts: List[float] = Field(description="List of attendance percentages for each day")
    screen_time_hours: List[float] = Field(description="List of screen time hours for each day")
    burnout_risk: int = Field(description="Calculated burnout risk from 1-10")
    productivity_index: float = Field(description="Aggregate productivity score (0-100)")

class SynthesizerOutput(BaseModel):
    analysis: str = Field(description="3-paragraph deep dive: 1. Trends, 2. Concerns, 3. Recommendations")
    metrics: PerformanceMetrics

class PlannerOutcome(BaseModel):
    proposed_slots: List[str] = Field(description="Exactly 4 suggested IST timeslots (e.g., '2026-01-12 10:00 AM')")
    meeting_agenda: str = Field(description="Brief summary of discussion")
    required_attendees: List[str] = Field(description="List of roles or IDs")

class TransferApplication(BaseModel):
    emp_id: str
    transfer_type: str
    current_zone: str
    desired_zone: str
    reason: str
    additional_details: Optional[str] = None

class AdminOutcome(BaseModel):
    status: bool = Field(description="Whether the transfer request complies with policies")
    reasoning: str = Field(description="Explanation for the decision based on context")

class TransferVerdictRequest(BaseModel):
    emp_id: str
    verdict: str
    manager_notes: str

class StartRequest(BaseModel):
    emp_id: str
    task: str
    description: str

class SelectSlotRequest(BaseModel):
    thread_id: str
    selected_slot: str

class GrievanceApplication(BaseModel):
    emp_id: str
    grievance_type: str = Field(alias="Grievance Type")
    subject: str = Field(alias="Subject")
    description: str = Field(alias="Description")

class CheckingOutcome(BaseModel):
    is_valid: bool = Field(description="Whether the grievance complies with company policy")
    reasoning: str = Field(description="Concise justification citing exact HR-POL codes")

class GrievanceVerdictRequest(BaseModel):
    emp_id: str
    verdict: str
    manager_notes: str

"""
=====================================================
Proposed Slot : 12th January 26, 9:00 a.m. IST
Meeting Agenda : Transfer discussion of employee
Required Attendees : E1012
=====================================================
"""