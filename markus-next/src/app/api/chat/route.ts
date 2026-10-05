/**
 * Markus AI — Chat API Route (SSE Streaming)
 *
 * Handles intent classification, agent routing, and SSE streaming.
 */

import { NextRequest } from "next/server";
import { intentClassifier } from "@/lib/core/intent-classifier";
import { orchestrator } from "@/lib/agents/orchestrator";
import { memoryManager } from "@/lib/memory/memory-manager";
import { ragRetriever } from "@/lib/rag/retriever";
import { formatSSE, formatSSEDone, formatSSEError } from "@/lib/ai/streaming";
import { AgentType, IntentType, MemoryCategory } from "@/lib/config/constants";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const message = body.message || body.content || "";
    let agentType = body.agent_type || body.agentType;
    const streaming = body.stream !== false;

    if (!message || !message.trim()) {
      return new Response(JSON.stringify({ error: "Message is required" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    // 1. Classify intent
    let [intent, confidence] = intentClassifier.classifyWithConfidence(message);
    let [category] = intentClassifier.analyzeCategory(message, intent);

    // Direct system action interception
    const autoAgent = orchestrator.getAgent(AgentType.AUTOMATION) as any;
    if (autoAgent && typeof autoAgent.canHandleDirectAction === "function" && autoAgent.canHandleDirectAction(message)) {
      intent = IntentType.SYSTEM_CONTROL;
      confidence = 1.0;
      category = "task" as any;
      if (!agentType) agentType = AgentType.AUTOMATION;
    }

    // 2. Check RAG knowledge base
    const [ragContext] = ragRetriever.buildRagContext(message);

    // 3. Build context
    const context: Record<string, unknown> = {
      intent: intent,
      confidence: confidence,
      category: category,
    };
    if (ragContext) {
      context.rag_context = ragContext;
    }

    // 4. Store in memory
    memoryManager.store(`User: ${message}`, MemoryCategory.SESSION, [intent], 0.5);

    if (streaming) {
      // SSE Streaming response
      const encoder = new TextEncoder();

      const stream = new ReadableStream({
        async start(controller) {
          try {
            // Send metadata event
            const metaEvent = formatSSE(
              JSON.stringify({ intent, confidence, category, agent: agentType || intent }),
              "metadata",
            );
            controller.enqueue(encoder.encode(metaEvent));

            // Stream from agent
            let fullResponse = "";
            for await (const token of orchestrator.routeAndStream(message, agentType, context)) {
              fullResponse += token;
              controller.enqueue(encoder.encode(formatSSE(token)));
            }

            // Store AI response in memory
            memoryManager.store(`AI: ${fullResponse.slice(0, 500)}`, MemoryCategory.SESSION, [intent], 0.4);

            // Send done signal
            controller.enqueue(encoder.encode(formatSSEDone()));
          } catch (e) {
            const errorMsg = e instanceof Error ? e.message : String(e);
            controller.enqueue(encoder.encode(formatSSEError(errorMsg)));
          } finally {
            controller.close();
          }
        },
      });

      return new Response(stream, {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          "Connection": "keep-alive",
          "Access-Control-Allow-Origin": "*",
        },
      });
    } else {
      // Non-streaming response
      const result = await orchestrator.routeAndProcess(message, agentType, context);
      memoryManager.store(`AI: ${result.slice(0, 500)}`, MemoryCategory.SESSION, [intent], 0.4);

      return new Response(
        JSON.stringify({
          response: result,
          intent,
          confidence,
          category,
        }),
        {
          headers: { "Content-Type": "application/json" },
        },
      );
    }
  } catch (e) {
    const errorMsg = e instanceof Error ? e.message : String(e);
    console.error(`Chat API error: ${errorMsg}`);
    return new Response(
      JSON.stringify({ error: errorMsg }),
      { status: 500, headers: { "Content-Type": "application/json" } },
    );
  }
}
