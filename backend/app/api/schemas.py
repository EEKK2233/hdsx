from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    display_name: str
    role: str = Field(pattern="^(admin|teacher|student|parent)$")
    email: str | None = None


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)
    email: str | None = None


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    email: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(ORMModel):
    id: int
    public_id: str
    username: str
    email: str | None
    display_name: str
    role: str
    is_active: bool


class CourseCreate(BaseModel):
    name: str
    subject: str
    grade_level: str | None = None
    description: str | None = None


class CourseOut(ORMModel):
    id: int
    public_id: str
    name: str
    subject: str
    grade_level: str | None
    description: str | None
    owner_id: int
    status: str


class ChapterCreate(BaseModel):
    title: str
    parent_id: int | None = None
    sort_order: int = 0


class KnowledgePointCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    chapter_id: int | None = None


class JoinRequestCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class JoinRequestReview(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    comment: str | None = Field(default=None, max_length=500)


class CourseManagerAdd(BaseModel):
    user_id: int


class SearchRequest(BaseModel):
    course_id: int
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=8, ge=1, le=30)


class LessonGenerateRequest(BaseModel):
    course_id: int
    chapter_id: int | None = None
    chapter_title: str
    resource_type: str = Field(pattern="^(lesson_plan|lecture|ppt_outline|exercise)$")
    audience: str = "本科生"
    duration_minutes: int = Field(default=45, ge=10, le=240)
    requirements: str | None = None


class AssignmentCreate(BaseModel):
    course_id: int
    class_id: int | None = None
    title: str
    description: str | None = None
    due_at: datetime | None = None


class QuestionCreate(BaseModel):
    question_type: str = Field(pattern="^(single_choice|multiple_choice|true_false|short_answer|essay)$")
    stem: str
    standard_answer: str
    options: list[dict] | None = None
    rubric: list[dict] | None = None
    knowledge_point_ids: list[int] = Field(default_factory=list)
    max_score: Decimal = Field(gt=0)
    sort_order: int = 0


class SubmissionCreate(BaseModel):
    answers: list[dict]


class ReviewRequest(BaseModel):
    final_score: Decimal = Field(ge=0)
    feedback: str


class ParentLinkCreate(BaseModel):
    parent_id: int
    student_id: int


class ReportReviewRequest(BaseModel):
    action: str = Field(pattern="^(approve|publish|reject)$")
    comment: str | None = None


class QASessionCreate(BaseModel):
    course_id: int
    title: str = "新对话"


class QAMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ReportGenerateRequest(BaseModel):
    student_id: int
    course_id: int
    period_type: str = Field(pattern="^(week|month)$")
    period_start: datetime
    period_end: datetime
