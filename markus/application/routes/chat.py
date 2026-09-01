"""
Markus AI — Chat API Routes

/api/chat — streaming chat with intent-based agent routing
"""

from __future__ import annotations

import json
import logging
from uuid import uuid4

import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.orchestrator import orchestrator
from core.context_manager import context_manager
from core.intent_classifier import intent_classifier
from ai.streaming import stream_to_sse
from memory.memory_manager import memory_manager
from config.constants import MemoryCategory, MemoryType, AIState, IntentType
from application.websocket import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])

INTENT_TO_AISTATE: dict[IntentType, AIState] = {
    IntentType.CODE: AIState.CODING,
    IntentType.DEBUG: AIState.CODING,
    IntentType.REVIEW: AIState.CODING,
    IntentType.RESEARCH: AIState.RESEARCH,
    IntentType.ARCHITECTURE: AIState.PLANNING,
    IntentType.AUTOMATION: AIState.EXECUTING,
    IntentType.SYSTEM_CONTROL: AIState.EXECUTING,
    IntentType.CHAT: AIState.THINKING,
}


class ChatRequest(BaseModel):
    message: str
    conversation_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_type: str | None = None
    stream: bool = True


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    agent_used: str | None = None
    intent: str | None = None


@router.post("")
@router.post("/")
async def chat(request: ChatRequest):
    """Send a message to Markus. Streams the response via SSE."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Classify intent & analyze category (question vs task)
    category, intent = intent_classifier.analyze_category(request.message)
    work_state = INTENT_TO_AISTATE.get(intent, AIState.THINKING)

    # Track in context
    ctx = context_manager.get_or_create_context(request.conversation_id)
    context_manager.add_message(request.conversation_id, "user", request.message)

    # Save to short-term memory
    memory_manager.save(
        content=f"User: {request.message}",
        category=MemoryCategory.TEMPORARY,
        memory_type=MemoryType.SHORT_TERM,
    )

    # Broadcast initial work state to orb
    await ws_manager.set_state(work_state)

    if request.stream:
        async def generate():
            full_response = ""
            try:
                async for token in orchestrator.route_and_stream(
                    request.message,
                    agent_type=request.agent_type,
                ):
                    full_response += token
                    yield f"data: {json.dumps({'content': token, 'intent': intent.value, 'category': category, 'state': work_state.value})}\n\n"

                # Save assistant response to context
                context_manager.add_message(request.conversation_id, "assistant", full_response)

                # Final event
                yield f"data: {json.dumps({'done': True, 'intent': intent.value, 'category': category, 'state': AIState.SUCCESS.value})}\n\n"

                # Broadcast success and reset to idle
                await ws_manager.set_state(AIState.SUCCESS)
                await asyncio.sleep(0.5)
                await ws_manager.set_state(AIState.IDLE)
            except Exception as e:
                await ws_manager.set_state(AIState.ERROR)
                raise e

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        try:
            response = await orchestrator.route_and_process(
                request.message,
                agent_type=request.agent_type,
            )
            context_manager.add_message(request.conversation_id, "assistant", response)
            await ws_manager.set_state(AIState.SUCCESS)
            
            async def _reset():
                await asyncio.sleep(0.5)
                await ws_manager.set_state(AIState.IDLE)
            asyncio.create_task(_reset())

            return ChatResponse(
                conversation_id=request.conversation_id,
                message=response,
                intent=intent.value,
            )
        except Exception as e:
            await ws_manager.set_state(AIState.ERROR)
            raise e


@router.get("/conversations")
async def list_conversations():
    """List active conversations."""
    return {"conversations": context_manager.list_active_conversations()}


@router.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear a conversation."""
    context_manager.clear_context(conversation_id)
    return {"status": "cleared"}
