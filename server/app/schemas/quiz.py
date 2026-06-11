from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class QuestionCreate(BaseModel):
    type: str = Field(..., description="Question type like 'single_choice' or 'multiple_choice'")
    title: str = Field(..., description="Short title or text of the question")
    content: Optional[str] = Field(None, description="Expanded text or array of answer options")
    attachments: Optional[List[str]] = None
    answer: Dict[str, Any] = Field(..., description="Object with correct answers and explanations")

class QuizCreate(BaseModel):
    course_id: Optional[str] = None
    name: str
    about: Optional[str] = None
    attachments: Optional[List[str]] = None
    attempts_allowed: int = 0
    questions: List[QuestionCreate] = Field(..., description="Масив питань для цього квізу")

class AnswerSubmit(BaseModel):
    question_id: str
    selected_option: Any  # Any, because it can be a string for single choice or list for multiple choice

class QuizFinishRequest(BaseModel):
    attempt_id: str
    answers: List[AnswerSubmit]