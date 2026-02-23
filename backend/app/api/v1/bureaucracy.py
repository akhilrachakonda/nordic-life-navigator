"""
Bureaucracy API — streaming chat endpoint for Swedish bureaucracy queries.

This is a thin HTTP adapter. All business logic lives in BureaucracyService.
Includes: rate limiting, client disconnect detection, SSE streaming.
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.security import get_current_user
from app.core.dependencies import get_bureaucracy_service
from app.core.rate_limiter import rate_limiter
from app.schemas.chat import ChatRequest, StreamEvent
from app.services.bureaucracy_service import BureaucracyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bureaucracy", tags=["bureaucracy"])


@router.post("/chat")
async def chat(
    request_body: ChatRequest,
    request: Request,
    user: dict = Depends(get_current_user),
    service: BureaucracyService = Depends(get_bureaucracy_service),
) -> StreamingResponse:
    """
    Stream a bureaucracy-aware AI response using RAG.

    Sends Server-Sent Events (SSE) with token chunks.
    Enforces per-user rate limiting and detects client disconnects.
    """
    user_id = user["uid"]

    # Rate limit check
    rate_limiter.check(user_id)

    async def event_generator():
        conversation_id = request_body.conversation_id

        # Emit the conversation_id so the client knows where to find it
        if conversation_id is None:
            conversation_id = service.get_conversation_id()

        start_event = StreamEvent(conversation_id=conversation_id)
        yield f"data: {start_event.model_dump_json()}\n\n"

        try:
            async for token in service.stream_chat(
                user_id=user_id,
                conversation_id=conversation_id,
                message=request_body.message,
            ):
                # Check if client has disconnected
                if await request.is_disconnected():
                    logger.info(
                        "Client disconnected mid-stream (user=%s, conv=%s)",
                        user_id,
                        conversation_id,
                    )
                    return

                event = StreamEvent(token=token)
                yield f"data: {event.model_dump_json()}\n\n"

            done_event = StreamEvent(done=True)
            yield f"data: {done_event.model_dump_json()}\n\n"

        except Exception as e:
            logger.error("Unexpected error in chat stream: %s", e)
            error_event = StreamEvent(
                error=True,
                error_message="The AI service is temporarily unavailable. Please try again.",
                error_code="INTERNAL_ERROR",
            )
            yield f"data: {error_event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations")
async def list_conversations(
    user: dict = Depends(get_current_user),
    service: BureaucracyService = Depends(get_bureaucracy_service),
):
    """List all conversations for the authenticated user."""
    conversations = await service.get_conversations(user["uid"])
    return {"conversations": conversations}
