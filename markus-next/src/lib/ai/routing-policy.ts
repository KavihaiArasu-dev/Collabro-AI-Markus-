/**
 * Markus AI — Routing Policy (§6a)
 *
 * Provider tier definitions and Markus-level routing policy.
 */

import { RouteAlias, ProviderTier, IntentType } from "@/lib/config/constants";

export interface RoutingContext {
  taskType: string;
  privacy: string;
  latency: string;
  complexity: string;
  agentType?: string;
}

class RoutingPolicy {
  // Provider tiers for informational purposes
  static readonly TIERS: Record<ProviderTier, { name: string; providers: string[]; useCases: string }> = {
    [ProviderTier.TIER_A]: {
      name: "General Intelligence",
      providers: ["Gemini", "Claude", "OpenAI", "DeepSeek", "Mistral", "Qwen"],
      useCases: "Complex reasoning, long context, architecture, hard coding, planning",
    },
    [ProviderTier.TIER_B]: {
      name: "Fast Intelligence",
      providers: ["Groq", "Cerebras"],
      useCases: "Short answers, intent classification, quick tool decisions, UI commands",
    },
    [ProviderTier.TIER_C]: {
      name: "Local Intelligence",
      providers: ["Ollama", "LM Studio", "vLLM"],
      useCases: "Private requests, offline operation, sensitive local context, dev/testing",
    },
  };

  // Intent → route mapping
  static readonly INTENT_ROUTES: Record<IntentType, RouteAlias> = {
    [IntentType.CHAT]: RouteAlias.AUTO,
    [IntentType.QUESTION]: RouteAlias.FAST,
    [IntentType.SEARCH]: RouteAlias.FAST,
    [IntentType.CODE]: RouteAlias.CODING,
    [IntentType.DEBUG]: RouteAlias.SMART,
    [IntentType.FILE_OPERATION]: RouteAlias.FAST,
    [IntentType.APP_CONTROL]: RouteAlias.FAST,
    [IntentType.SYSTEM_CONTROL]: RouteAlias.FAST,
    [IntentType.BROWSER_AUTOMATION]: RouteAlias.FAST,
    [IntentType.RESEARCH]: RouteAlias.AUTO,
    [IntentType.AUTOMATION]: RouteAlias.FAST,
    [IntentType.REVIEW]: RouteAlias.CODING,
    [IntentType.ARCHITECTURE]: RouteAlias.SMART,
    [IntentType.DOCUMENTATION]: RouteAlias.AUTO,
    [IntentType.TASK_MANAGEMENT]: RouteAlias.AUTO,
    [IntentType.MULTI_STEP_ACTION]: RouteAlias.SMART,
    [IntentType.MEMORY]: RouteAlias.FAST,
    [IntentType.RAG]: RouteAlias.AUTO,
    [IntentType.SETTINGS]: RouteAlias.FAST,
    [IntentType.VOICE_COMMAND]: RouteAlias.FAST,
    [IntentType.YOUTUBE]: RouteAlias.FAST,
  };

  /**
   * Resolve the OmniRoute routing alias based on task context.
   *
   * Priority order (from spec §6a):
   * 1. Privacy == local → /offline
   * 2. Task type == coding → /coding
   * 3. Latency == fast → /fast
   * 4. Complexity == high → /smart
   * 5. Default → auto
   */
  resolveRoute(context: RoutingContext): string {
    let route: RouteAlias;

    if (context.privacy === "local") {
      route = RouteAlias.OFFLINE;
    } else if (context.taskType === "coding" || context.taskType === "code") {
      route = RouteAlias.CODING;
    } else if (context.latency === "fast") {
      route = RouteAlias.FAST;
    } else if (context.complexity === "high") {
      route = RouteAlias.SMART;
    } else {
      route = RouteAlias.AUTO;
    }

    return route;
  }

  resolveForIntent(intent: IntentType): string {
    const route = RoutingPolicy.INTENT_ROUTES[intent] ?? RouteAlias.AUTO;
    return route;
  }

  private static readonly TIER_INFO_CACHE: Record<string, { name: string; providers: string[]; useCases: string }> = Object.freeze({ ...RoutingPolicy.TIERS });

  getTierInfo(): Record<string, { name: string; providers: string[]; useCases: string }> {
    return RoutingPolicy.TIER_INFO_CACHE;
  }
}

// Singleton
export const routingPolicy = new RoutingPolicy();
