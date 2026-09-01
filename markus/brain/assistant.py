"""
Markus AI — Core Personal Assistant Coordinator (§1, §2, §6)
Fuses multimodal perception context (face + emotion), RAG document retrieval,
intelligent model routing, and safe system execution into a unified personal assistant.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator, Dict, List, Optional
from domain.entities import ChatMessage, MessageRole
from brain.perception import perception_manager
from rag.retriever import rag_retriever
from ai.omniroute_client import omniroute_client
from core.model_router import model_router

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are Markus, a personal AI development assistant operating on Clean Architecture principles.
You are running locally on the user's machine with full privacy-first capabilities.

Capabilities:
- Software development, full-stack coding (Python, Java, TypeScript, React, C++, Rust, Go), debugging, and architectural design.
- Answering general knowledge, scientific, mathematical, and personal assistant queries.
- Incorporating local user documents through Retrieval-Augmented Generation (RAG).
- Attuned to user presence and real-time facial expressions.

Personal Persona:
- Helpful, sharp, concise, direct, and friendly.
- Format code in clean, highlighted markdown blocks with language tags.
- When answering from user documents (RAG), cite the document source.

{perception_context}

{rag_context}
"""


class PersonalAssistant:
    """
    Orchestrates user queries by fusing perception, RAG knowledge, and AI generation.
    """

    def __init__(self):
        self.history: List[ChatMessage] = []

    def build_system_prompt(self, user_query: str) -> str:
        """Construct multimodal prompt incorporating perception state and RAG context."""
        # 1. Perception Context (User Face, Emotion, Screen)
        ctx = perception_manager.get_context()
        perception_str = ctx.to_prompt_context()

        # 2. RAG Document Retrieval Context
        rag_str, _ = rag_retriever.build_rag_context(user_query, top_k=3)

        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            perception_context=perception_str if perception_str else "[Perception: Laptop Camera & Microphone Active]",
            rag_context=rag_str if rag_str else "",
        )
        return prompt.strip()

    async def generate_response(
        self,
        user_query: str,
        mode: str = "normal",
    ) -> str:
        """
        Generate answer via OmniRoute gateway or local fallback.
        """
        system_prompt = self.build_system_prompt(user_query)

        messages = [
            {"role": "system", "content": system_prompt},
            *[{"role": m.role.value, "content": m.content} for m in self.history[-6:]],
            {"role": "user", "content": user_query},
        ]

        # Record to history
        self.history.append(ChatMessage(role=MessageRole.USER, content=user_query))

        try:
            # Route through OmniRoute Client
            content = await omniroute_client.generate(messages=messages, route=mode)
            if content:
                self.history.append(ChatMessage(role=MessageRole.ASSISTANT, content=content))
                return content
        except Exception as e:
            logger.warning(f"OmniRoute gateway unavailable: {e}. Generating offline response.")

        # Offline Local Fallback
        fallback = self._generate_local_fallback(user_query)
        self.history.append(ChatMessage(role=MessageRole.ASSISTANT, content=fallback))
        return fallback

    async def generate_stream(
        self,
        user_query: str,
        mode: str = "normal",
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens to the client."""
        system_prompt = self.build_system_prompt(user_query)
        messages = [
            {"role": "system", "content": system_prompt},
            *[{"role": m.role.value, "content": m.content} for m in self.history[-6:]],
            {"role": "user", "content": user_query},
        ]

        self.history.append(ChatMessage(role=MessageRole.USER, content=user_query))
        full_content = ""

        try:
            async for token in omniroute_client.generate_stream(messages=messages, route=mode):
                full_content += token
                yield token

            if full_content:
                self.history.append(ChatMessage(role=MessageRole.ASSISTANT, content=full_content))
                return
        except Exception as e:
            logger.warning(f"Stream error: {e}. Falling back.")

        fallback = self._generate_local_fallback(user_query)
        self.history.append(ChatMessage(role=MessageRole.ASSISTANT, content=fallback))
        yield fallback

    def _generate_local_fallback(self, query: str) -> str:
        """Deterministic offline answering when gateway is in offline mode."""
        q = query.lower().strip()

        # Check RAG matches first
        rag_str, matches = rag_retriever.build_rag_context(query, top_k=2)
        if matches:
            top_match = matches[0]
            return (
                f"**From your local knowledge base (`{top_match.chunk.doc_name}`):**\n\n"
                f"{top_match.chunk.text}\n\n"
                f"*(Retrieved via Markus RAG with {int(top_match.similarity_score * 100)}% match)*"
            )

        if "who are you" in q or "what is your name" in q or "what are you" in q:
            return (
                "I am **Markus AI**, your personal development assistant. "
                "I operate on Clean Architecture principles, incorporating voice wake-up, "
                "laptop camera face recognition, real-time emotion estimation, and RAG document knowledge."
            )

        if "hello" in q or "hey" in q or "hi" in q:
            ctx = perception_manager.get_context()
            face_info = f"I see you're looking {ctx.vision.expression} today." if ctx.vision.face_present else "How can I help you today?"
            return f"Hello! {face_info} What would you like to build or explore?"

        return (
            f"I have processed your query: **\"{query}\"**.\n\n"
            "To connect me to live multi-model LLMs (OpenAI, Gemini, Anthropic, Ollama, DeepSeek), "
            "ensure **OmniRoute** is running (`omniroute serve`) or add your API key in **AI MODEL / KEY** settings on the HUD."
        )


personal_assistant = PersonalAssistant()
