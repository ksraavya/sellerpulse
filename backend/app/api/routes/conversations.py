"""Session endpoints for the SP-06 conversation engine."""
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.conversations.graph import get_conversation_graph
from app.schemas.conversation import (
    ConversationResponse,
    CreateConversationRequest,
    SendMessageRequest,
)
from app.services.seller_service import SellerService
from app.repositories.json_seller_repository import JsonSellerRepository
from app.core.config import get_seller_data_dir

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _seller_exists(seller_id: str) -> bool:
    service = SellerService(JsonSellerRepository(get_seller_data_dir()))
    try:
        service.get_seller_context(seller_id)
        return True
    except LookupError:
        return False


@router.post("", response_model=ConversationResponse, status_code=201)
def create_conversation(payload: CreateConversationRequest) -> dict:
    if not _seller_exists(payload.seller_id):
        raise HTTPException(status_code=404, detail="Seller not found.")
    session_id = str(uuid4())
    return get_conversation_graph().create_session(session_id, payload.seller_id)


@router.post("/{session_id}/messages", response_model=ConversationResponse)
def send_message(session_id: str, payload: SendMessageRequest) -> dict:
    result = get_conversation_graph().send_message(session_id, payload.content)
    if result is None:
        raise HTTPException(status_code=404, detail="Conversation session not found.")
    return result


@router.get("/{session_id}", response_model=ConversationResponse)
def get_conversation(session_id: str) -> dict:
    result = get_conversation_graph().get_session(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Conversation session not found.")
    return result
