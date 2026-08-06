"""Smart question bank endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.common import MessageResponse
from app.services.question_bank_service import QuestionBankService

router = APIRouter(prefix="/questions", tags=["questions"])


class QuestionUpsert(BaseModel):
    question: str = Field(min_length=2)
    answer: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    portals: list[str] = Field(default_factory=list)


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


@router.delete("/{qa_id}", response_model=MessageResponse)
async def delete_question(qa_id: str, user: User = Depends(get_current_user)):
    await QuestionBankService().delete(str(user.id), qa_id)
    return MessageResponse(detail="Deleted")
