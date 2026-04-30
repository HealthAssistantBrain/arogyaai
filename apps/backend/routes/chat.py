from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.api_models import ChatRequest
from services.chat_service import generate_chat_response

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


@router.post("", response_model=None)
async def chat_with_assistant(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    try:
        return await generate_chat_response(
            str(current_user.id),
            payload.query,
            db=db,
            current_user=current_user,
            conversation_history=[item.model_dump() for item in payload.history],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
