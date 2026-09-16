/**
 * Markus AI — Streaming Support
 *
 * SSE (Server-Sent Events) utilities for real-time AI response streaming.
 * Direct port from ai/streaming.py.
 */

export function formatSSE(data: string, event: string = "message"): string {
  return `event: ${event}\ndata: ${JSON.stringify({ content: data })}\n\n`;
}

export function formatSSEDone(): string {
  return `event: done\ndata: ${JSON.stringify({ content: "[DONE]" })}\n\n`;
}

export function formatSSEError(error: string): string {
  return `event: error\ndata: ${JSON.stringify({ error })}\n\n`;
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
