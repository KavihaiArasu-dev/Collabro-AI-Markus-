"""
Markus AI — Context Manager (§4, §6c)

Merges voice/vision/screen/app state + memory into a unified context
object that's sent to the LLM alongside the user's message.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from brain.perception import PerceptionContext, perception_manager
from vision.screen import screen_perception, ScreenContext

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """The unified context assembled for each LLM call."""
    # Core conversation
    conversation_id: str = ""
    messages: list[dict] = field(default_factory=list)

    # User context
    user_id: str = ""
    user_preferences: dict = field(default_factory=dict)

    # Current state
    current_project: Optional[str] = None
    current_file: Optional[str] = None
    current_agent: Optional[str] = None

    # Memory fragments (retrieved from layered memory)
    short_term_memory: list[str] = field(default_factory=list)
    episodic_memory: list[str] = field(default_factory=list)
    project_memory: list[str] = field(default_factory=list)

    # RAG context (retrieved documents)
    rag_context: list[str] = field(default_factory=list)

    # Multimodal Perception state (§6c)
    perception: Optional[PerceptionContext] = None

    # Screen perception state (§3, §6c)
    screen: Optional[ScreenContext] = None

    # System state
    system_metrics: dict = field(default_factory=dict)

    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ContextManager:
    """
    Assembles the full context for each AI interaction.

    Responsibilities:
    - Merge conversation history
    - Inject multimodal perception context (speech & facial emotion signals)
    - Inject active screen & foreground window context
    - Pull relevant memory fragments
    - Include RAG-retrieved documents
    - Add system/app state
    - Format everything into a coherent context for the LLM
    """

    def __init__(self):
        self._active_contexts: dict[str, ConversationContext] = {}
        logger.info("Context Manager initialized")

    def create_context(self, conversation_id: str) -> ConversationContext:
        """Create a new conversation context."""
        ctx = ConversationContext(conversation_id=conversation_id)
        ctx.perception = perception_manager.get_context()
        ctx.screen = screen_perception.get_active_window_context()
        self._active_contexts[conversation_id] = ctx
        return ctx

    def get_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get an existing conversation context."""
        return self._active_contexts.get(conversation_id)

    def get_or_create_context(self, conversation_id: str) -> ConversationContext:
        """Get existing or create new context with fresh perception & screen state."""
        if conversation_id not in self._active_contexts:
            return self.create_context(conversation_id)
        ctx = self._active_contexts[conversation_id]
        ctx.perception = perception_manager.get_context()
        ctx.screen = screen_perception.get_active_window_context()
        return ctx

    def add_message(self, conversation_id: str, role: str, content: str):
        """Add a message to the conversation context."""
        ctx = self.get_or_create_context(conversation_id)
        ctx.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

    def build_prompt_messages(
        self,
        ctx: ConversationContext,
        system_prompt: str = "",
        max_messages: int = 50,
    ) -> list[dict]:
        """
        Build the final message list for the LLM call.

        Merges:
        1. System prompt (with multimodal context & screen context injections)
        2. Memory fragments
        3. RAG context
        4. Conversation history (truncated to max_messages)
        """
        messages = []

        # Build enriched system prompt
        enriched_system = self._build_system_prompt(ctx, system_prompt)
        if enriched_system:
            messages.append({"role": "system", "content": enriched_system})

        # Add conversation history (most recent messages)
        history = ctx.messages[-max_messages:]
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        return messages

    def _build_system_prompt(self, ctx: ConversationContext, base_prompt: str) -> str:
        """Inject context into the system prompt."""
        parts = []

        if base_prompt:
            parts.append(base_prompt)

        # Add Language Directive (§6)
        from config.settings import settings
        if settings.voice.language.lower().startswith("ta"):
            parts.append(
                "\n## Language Directive\n"
                "You communicate primarily in Tamil (தமிழ்). "
                "All your responses, spoken dialogue, and conversational answers must be in natural, polite Tamil. "
                "You may use Tamil script or Tanglish as appropriate, and maintain standard English for technical terms or code. "
                "Never speak or reply in Hindi."
            )

        # Add Multimodal Perception Context (§6c)
        if ctx.perception:
            perception_str = ctx.perception.to_prompt_context()
            if perception_str:
                parts.append("\n## Multimodal Perception Context\n" + perception_str)

        # Add Active Screen & Application Context (§3, §6c)
        if ctx.screen:
            screen_str = ctx.screen.to_prompt_context()
            if screen_str:
                parts.append("\n## Screen & Environment Context\n" + screen_str)

        # Add memory context
        if ctx.short_term_memory:
            parts.append("\n## Recent Context\n" + "\n".join(ctx.short_term_memory))

        if ctx.project_memory:
            parts.append("\n## Project Context\n" + "\n".join(ctx.project_memory))

        if ctx.episodic_memory:
            parts.append("\n## Relevant Past Interactions\n" + "\n".join(ctx.episodic_memory))

        # Add RAG context
        if ctx.rag_context:
            parts.append("\n## Relevant Documents\n" + "\n".join(ctx.rag_context))

        # Add current state
        if ctx.current_project:
            parts.append(f"\n## Current Project: {ctx.current_project}")
        if ctx.current_file:
            parts.append(f"## Current File: {ctx.current_file}")

        return "\n".join(parts)

    def clear_context(self, conversation_id: str):
        """Clear a conversation context."""
        if conversation_id in self._active_contexts:
            del self._active_contexts[conversation_id]

    def list_active_conversations(self) -> list[str]:
        """List all active conversation IDs."""
        return list(self._active_contexts.keys())


# Singleton
context_manager = ContextManager()
