import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.api_models import ChatRequest
from services.chat_service import generate_chat_response, stream_chat_response

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])
logger = logging.getLogger("uvicorn.error")


def _stream_event(event_type: str, payload: dict) -> str:
    return json.dumps({"event": event_type, "data": payload}, default=str) + "\n"


def _stream_error_events(*, message: str, detail: str, status_code: int):
    error_payload = {
        "message": message,
        "detail": detail,
        "status_code": status_code,
    }
    final_payload = {
        "success": False,
        "status": "error",
        "source": "chat_route",
        "error": error_payload,
        "data": None,
    }
    yield _stream_event("error", error_payload)
    yield _stream_event("final", {"payload": final_payload, "done": True})


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
    except Exception as exc:
        logger.exception("Unhandled chat route failure for user=%s: %s", getattr(current_user, "id", None), exc)
        return {
            "success": False,
            "status": "error",
            "source": "chat_route",
            "error": {
                "message": "Unable to process chat request right now.",
                "detail": str(exc),
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
            "intent": None,
            "mode": None,
            "data": None,
        }


@router.post("/stream", response_model=None)
async def stream_chat_with_assistant(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    async def event_stream():
        try:
            async for chunk in stream_chat_response(
                str(current_user.id),
                payload.query,
                db=db,
                current_user=current_user,
                conversation_history=[item.model_dump() for item in payload.history],
            ):
                yield chunk
        except ValueError as exc:
            for event in _stream_error_events(
                message=str(exc),
                detail=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            ):
                yield event
        except Exception as exc:
            logger.exception("Unhandled chat stream route failure for user=%s: %s", getattr(current_user, "id", None), exc)
            for event in _stream_error_events(
                message="Unable to finish the chat stream right now.",
                detail=str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ):
                yield event

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
