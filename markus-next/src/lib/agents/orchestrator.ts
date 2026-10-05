/**
 * Markus AI — Agent Orchestrator (§5)
 *
 * Coordinates every agent. Routes tasks, manages workflows,
 * handles agent communication, and resolves conflicts.
 */

import { AgentType, IntentType } from "@/lib/config/constants";
import { intentClassifier } from "@/lib/core/intent-classifier";
import { eventBus } from "@/lib/core/event-bus";
import { BaseAgent } from "./base-agent";
import {
  CoderAgent, ArchitectAgent, ReviewerAgent, DebugAgent,
  ResearchAgent, DocumentationAgent, UIUXAgent, AutomationAgent, MemoryAgent,
} from "./implementations";

// Map intent types to agent types
const INTENT_TO_AGENT: Partial<Record<IntentType, AgentType>> = {
  [IntentType.CODE]: AgentType.CODER,
  [IntentType.DEBUG]: AgentType.DEBUGGER,
  [IntentType.REVIEW]: AgentType.REVIEWER,
  [IntentType.ARCHITECTURE]: AgentType.ARCHITECT,
  [IntentType.RESEARCH]: AgentType.RESEARCHER,
  [IntentType.QUESTION]: AgentType.RESEARCHER,
  [IntentType.SEARCH]: AgentType.RESEARCHER,
  [IntentType.DOCUMENTATION]: AgentType.DOCUMENTATION,
  [IntentType.AUTOMATION]: AgentType.AUTOMATION,
  [IntentType.FILE_OPERATION]: AgentType.AUTOMATION,
  [IntentType.APP_CONTROL]: AgentType.AUTOMATION,
  [IntentType.SYSTEM_CONTROL]: AgentType.AUTOMATION,
  [IntentType.TASK_MANAGEMENT]: AgentType.AUTOMATION,
  [IntentType.SETTINGS]: AgentType.AUTOMATION,
  [IntentType.BROWSER_AUTOMATION]: AgentType.AUTOMATION,
  [IntentType.YOUTUBE]: AgentType.AUTOMATION,
  [IntentType.VOICE_COMMAND]: AgentType.AUTOMATION,
  [IntentType.MULTI_STEP_ACTION]: AgentType.ARCHITECT,
  [IntentType.MEMORY]: AgentType.MEMORY,
  [IntentType.RAG]: AgentType.RESEARCHER,
  [IntentType.CHAT]: AgentType.RESEARCHER,
};

class Orchestrator {
  private _agents: Map<AgentType, BaseAgent>;

  constructor() {
    this._agents = new Map<AgentType, BaseAgent>([
      [AgentType.CODER, new CoderAgent()],
      [AgentType.ARCHITECT, new ArchitectAgent()],
      [AgentType.REVIEWER, new ReviewerAgent()],
      [AgentType.DEBUGGER, new DebugAgent()],
      [AgentType.RESEARCHER, new ResearchAgent()],
      [AgentType.DOCUMENTATION, new DocumentationAgent()],
      [AgentType.UI_UX, new UIUXAgent()],
      [AgentType.AUTOMATION, new AutomationAgent()],
      [AgentType.MEMORY, new MemoryAgent()],
    ]);

    console.log(`Orchestrator initialized with ${this._agents.size} agents`);
  }

  getAgent(agentType: AgentType): BaseAgent | undefined {
    return this._agents.get(agentType);
  }

  async routeAndProcess(
    userInput: string,
    agentType?: string,
    context?: Record<string, unknown>,
  ): Promise<string> {
    let targetAgentType: AgentType;

    if (agentType) {
      if (Object.values(AgentType).includes(agentType as AgentType)) {
        targetAgentType = agentType as AgentType;
      } else {
        return `Unknown agent type: ${agentType}`;
      }
    } else {
      const intent = (context?.intent as IntentType) || intentClassifier.classify(userInput);
      targetAgentType = INTENT_TO_AGENT[intent] ?? AgentType.RESEARCHER;
    }

    const agent = this._agents.get(targetAgentType);
    if (!agent) {
      targetAgentType = AgentType.RESEARCHER;
    }

    const finalAgent = this._agents.get(targetAgentType)!;

    await eventBus.emit("task_routed", "orchestrator", {
      agent: targetAgentType,
      input: userInput.slice(0, 200),
    });

    console.log(`Task routed to ${targetAgentType}: ${userInput.slice(0, 80)}...`);
    return finalAgent.process(userInput, context);
  }

  async *routeAndStream(
    userInput: string,
    agentType?: string,
    context?: Record<string, unknown>,
  ): AsyncGenerator<string> {
    let targetAgentType: AgentType;

    if (agentType) {
      if (Object.values(AgentType).includes(agentType as AgentType)) {
        targetAgentType = agentType as AgentType;
      } else {
        yield `Unknown agent type: ${agentType}`;
        return;
      }
    } else {
      const intent = (context?.intent as IntentType) || intentClassifier.classify(userInput);
      targetAgentType = INTENT_TO_AGENT[intent] ?? AgentType.RESEARCHER;
    }

    const agent = this._agents.get(targetAgentType);
    if (!agent) {
      yield "No agent available for this task.";
      return;
    }

    yield* agent.processStream(userInput, context);
  }

  getAllAgentStatuses(): Record<string, unknown>[] {
    return Array.from(this._agents.values()).map((agent) => agent.getStatus());
  }

  getAgentStatus(agentType: string): Record<string, unknown> | undefined {
    if (Object.values(AgentType).includes(agentType as AgentType)) {
      const agent = this._agents.get(agentType as AgentType);
      return agent?.getStatus();
    }
    return undefined;
  }

  listAgents(): Record<string, unknown>[] {
    return Array.from(this._agents.values()).map((agent) => ({
      type: agent.agentType,
      name: agent.name,
      status: agent.status,
      route: agent.defaultRoute,
      tasks_completed: agent.taskHistory.length,
    }));
  }
}

// Singleton
export const orchestrator = new Orchestrator();
