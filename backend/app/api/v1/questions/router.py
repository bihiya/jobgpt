"""Smart question bank endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.exceptions import NotFoundError
from app.core.kafka import publish
from app.dependencies.auth import get_current_user
from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.user import User
from app.schemas.common import MessageResponse
from app.services.question_bank_service import QuestionBankService

router = APIRouter(prefix="/questions", tags=["questions"])


class QuestionUpsert(BaseModel):
    question: str = Field(min_length=2)
    answer: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    portals: list[str] = Field(default_factory=list)


class AnswerAndResume(BaseModel):
    """Save one or more answers then resume a paused application."""

    application_id: str
    answers: list[QuestionUpsert] = Field(min_length=1)


@router.get("")
async def list_questions(user: User = Depends(get_current_user)):
    return await QuestionBankService().list(str(user.id))


@router.post("")
async def upsert_question(payload: QuestionUpsert, user: User = Depends(get_current_user)):
    item = await QuestionBankService().upsert(
        str(user.id),
        payload.question,
        payload.answer,
        tags=payload.tags,
        portals=payload.portals,
    )
    return {"id": str(item.id), "question": item.question, "answer": item.answer}


@router.post("/answer-and-resume")
async def answer_and_resume(payload: AnswerAndResume, user: User = Depends(get_current_user)):
    """Ask once → save to bank → republish job.apply."""
    app = await Application.get(payload.application_id)
    if not app or app.user_id != str(user.id):
        raise NotFoundError("Application not found")
    if app.status not in {ApplicationStatus.NEEDS_INPUT, ApplicationStatus.NEEDS_OTP}:
        # Allow resume from failed/pending too if user is fixing answers
        if app.status not in {
            ApplicationStatus.FAILED,
            ApplicationStatus.PENDING,
            ApplicationStatus.RETRYING,
        }:
            raise NotFoundError("Application is not waiting for input")

    bank = QuestionBankService()
    saved = []
    for item in payload.answers:
        doc = await bank.upsert(
            str(user.id),
            item.question,
            item.answer,
            tags=item.tags or ["from_apply"],
            portals=item.portals,
        )
        saved.append({"id": str(doc.id), "question": doc.question})

    app.status = ApplicationStatus.PENDING
    app.blocker_type = ""
    app.unknown_questions = []
    app.error_message = ""
    await app.save()

    await publish(
        "job.apply",
        {
            "user_id": str(user.id),
            "job_id": app.job_id,
            "application_id": str(app.id),
            "resume_id": app.resume_id,
            "resumed_from": "question_bank",
        },
        key=str(user.id),
    )
    return {
        "application_id": str(app.id),
        "saved": saved,
        "status": "queued",
    }


@router.delete("/{qa_id}", response_model=MessageResponse)
async def delete_question(qa_id: str, user: User = Depends(get_current_user)):
    await QuestionBankService().delete(str(user.id), qa_id)
    return MessageResponse(detail="Deleted")
