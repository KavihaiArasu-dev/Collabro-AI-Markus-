/**
 * Markus AI — Model Router (§6a)
 *
 * The Markus-level policy layer that decides *what kind* of model
 * capability is needed, then delegates to OmniRoute.
 * Direct port from core/model_router.py.
 */

import { omnirouteClient } from "@/lib/ai/omniroute-client";
import { routingPolicy, type RoutingContext } from "@/lib/ai/routing-policy";
import { AgentType, AGENT_DEFAULT_ROUTES } from "@/lib/config/constants";

class ModelRouter {
  /**
   * Route a request through OmniRoute based on context.
   */
  async generate(
    messages: Array<{ role: string; content: string }>,
    taskType: string = "chat",
    privacy: string = "normal",
    latency: string = "balanced",
    complexity: string = "normal",
    agentType?: string,
    systemPrompt?: string,
    temperature: number = 0.7,
    maxTokens: number = 4096,
  ): Promise<string> {
    const route = this._resolveRoute(taskType, privacy, latency, complexity, agentType);
    console.log(`Model Router: route=${route}, task=${taskType}, agent=${agentType}`);

    return omnirouteClient.generate(messages, route, temperature, maxTokens, systemPrompt);
  }

  /**
   * Stream a routed response from OmniRoute.
   */
  async *generateStream(
    messages: Array<{ role: string; content: string }>,
    taskType: string = "chat",
    privacy: string = "normal",
    latency: string = "balanced",
    complexity: string = "normal",
    agentType?: string,
    systemPrompt?: string,
    temperature: number = 0.7,
    maxTokens: number = 4096,
  ): AsyncGenerator<string> {
    const route = this._resolveRoute(taskType, privacy, latency, complexity, agentType);
    console.log(`Model Router (stream): route=${route}, task=${taskType}, agent=${agentType}`);

    yield* omnirouteClient.generateStream(messages, route, temperature, maxTokens, systemPrompt);
  }

  private _resolveRoute(
    taskType: string,
    privacy: string,
    latency: string,
    complexity: string,
    agentType?: string,
  ): string {
    // Check agent-specific default first
    if (agentType) {
      const at = agentType as AgentType;
      if (at in AGENT_DEFAULT_ROUTES) {
        const agentRoute = AGENT_DEFAULT_ROUTES[at as AgentType];
        if (privacy === "local" || ["coding", "code"].includes(taskType) ||
            latency === "fast" || complexity === "high") {
          // Fall through to context-based routing
        } else {
          return agentRoute;
        }
      }
    }

    // Context-based routing
    const context: RoutingContext = {
      taskType,
      privacy,
      latency,
      complexity,
      agentType,
    };
    return routingPolicy.resolveRoute(context);
  }

  resolveRoutingDetails(
    taskType: string = "chat",
    privacy: string = "normal",
    latency: string = "balanced",
    complexity: string = "normal",
    agentType?: string,
  ): Record<string, unknown> {
    const route = this._resolveRoute(taskType, privacy, latency, complexity, agentType);
    let rationale = "default";
    if (privacy === "local") {
      rationale = "Privacy-first offline routing rule";
    } else if (["coding", "code"].includes(taskType)) {
      rationale = "Code generation & refactoring routing rule";
    } else if (latency === "fast") {
      rationale = "Low-latency fast execution routing rule";
    } else if (complexity === "high") {
      rationale = "High-complexity adaptive reasoning routing rule";
    } else if (agentType) {
      rationale = `Agent default routing rule (${agentType})`;
    }

    const tierInfo = ["auto", "/smart"].includes(route)
      ? "Tier A (General)"
      : ["/fast", "/cheap"].includes(route)
        ? "Tier B (Fast)"
        : "Tier C (Local/Offline)";

    return {
      route,
      rationale,
      tier: tierInfo,
      context: { taskType, privacy, latency, complexity, agentType },
    };
  }

  async checkGatewayStatus(): Promise<Record<string, unknown>> {
    const connected = await omnirouteClient.checkConnection();
    const models = connected ? await omnirouteClient.listModels() : [];

    return {
      connected,
      gateway_url: process.env.OMNIROUTE_BASE_URL ?? "http://localhost:20128/v1",
      available_models: models,
      model_count: models.length,
    };
  }
}

// Singleton
export const modelRouter = new ModelRouter();
