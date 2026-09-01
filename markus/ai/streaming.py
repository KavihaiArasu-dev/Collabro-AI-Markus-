"""
Markus AI — Streaming Support

SSE (Server-Sent Events) utilities for real-time AI response streaming.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


async def format_sse(data: str, event: str = "message") -> str:
    """Format data as an SSE event string."""
    return f"event: {event}\ndata: {json.dumps({'content': data})}\n\n"


async def format_sse_done() -> str:
    """Format the SSE stream-done signal."""
    return f"event: done\ndata: {json.dumps({'content': '[DONE]'})}\n\n"


async def format_sse_error(error: str) -> str:
    """Format an SSE error event."""
    return f"event: error\ndata: {json.dumps({'error': error})}\n\n"


async def stream_to_sse(
    token_stream: AsyncGenerator[str, None],
    include_done: bool = True,
) -> AsyncGenerator[str, None]:
    """
    Convert a token stream into SSE-formatted events.

    Args:
        token_stream: Async generator yielding token strings.
        include_done: Whether to send a [DONE] event at the end.

    Yields:
        SSE-formatted strings.
    """
    try:
        async for token in token_stream:
            yield await format_sse(token)
    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield await format_sse_error(str(e))
    finally:
        if include_done:
            yield await format_sse_done()
