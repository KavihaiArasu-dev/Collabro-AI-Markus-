/**
 * Markus AI — Streaming Support
 *
 * SSE (Server-Sent Events) utilities for real-time AI response streaming.
 * Direct port from ai/streaming.py.
 */

export function formatSSE(data: string, event: string = "message"): string {
  if (event === "metadata") {
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(data);
    } catch {
      parsed = { content: data };
    }
    return `event: metadata\ndata: ${JSON.stringify({ type: "metadata", ...parsed })}\n\n`;
  }
  return `event: ${event}\ndata: ${JSON.stringify({ type: "chunk", content: data })}\n\n`;
}

export function formatSSEDone(): string {
  return `event: done\ndata: ${JSON.stringify({ type: "done", content: "[DONE]", done: true })}\n\n`;
}

export function formatSSEError(error: string): string {
  return `event: error\ndata: ${JSON.stringify({ type: "error", error })}\n\n`;
}

/**
 * Convert a token async iterable into SSE-formatted strings.
 */
export async function* streamToSSE(
  tokenStream: AsyncIterable<string>,
  includeDone: boolean = true,
): AsyncGenerator<string> {
  try {
    for await (const token of tokenStream) {
      yield formatSSE(token);
    }
  } catch (e) {
    const errorMsg = e instanceof Error ? e.message : String(e);
    console.error(`Stream error: ${errorMsg}`);
    yield formatSSEError(errorMsg);
  } finally {
    if (includeDone) {
      yield formatSSEDone();
    }
  }
}
