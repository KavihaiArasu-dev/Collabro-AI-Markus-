/**
 * Markus AI — Base Agent (§5)
 *
 * Abstract base class for all specialized agents.
 * Every agent routes model calls through the ModelRouter → OmniRoute chain.
 * Direct port from agents/base_agent.py.
 */

import { AgentType, AgentStatus, RouteAlias, AGENT_DEFAULT_ROUTES } from "@/lib/config/constants";
import { modelRouter } from "@/lib/core/model-router";
import { eventBus } from "@/lib/core/event-bus";
import { v4 as uuidv4 } from "uuid";

export interface AgentTask {
  id: string;
  description: string;
  inputData: unknown;
  result?: string;
  status: string;
  startedAt?: string;
  completedAt?: string;
}

export abstract class BaseAgent {
  agentType: AgentType;
  status: AgentStatus = AgentStatus.IDLE;
  currentTask: AgentTask | null = null;
  taskHistory: AgentTask[] = [];
  defaultRoute: RouteAlias;
  createdAt: string;

  constructor(agentType: AgentType) {
    this.agentType = agentType;
    this.defaultRoute = AGENT_DEFAULT_ROUTES[agentType] ?? RouteAlias.AUTO;
    this.createdAt = new Date().toISOString();
    console.log(`Agent initialized: ${agentType} (route: ${this.defaultRoute})`);
  }

  abstract get systemPrompt(): string;

  get name(): string {
    return this.agentType;
  }

  async process(userInput: string, context?: Record<string, unknown>): Promise<string> {
    const task: AgentTask = {
      id: uuidv4().slice(0, 8),
      description: userInput.slice(0, 200),
      inputData: userInput,
      status: "in_progress",
      startedAt: new Date().toISOString(),
    };
    this.currentTask = task;
    this.status = AgentStatus.ACTIVE;

    await eventBus.emit("agent_status_change", this.name, {
      agent: this.name,
      status: "active",
      task: task.description,
    });

    try {
      const messages: Array<{ role: string; content: string }> = [
        { role: "user", content: userInput },
      ];

      if (context) {
        const contextStr = Object.entries(context)
          .map(([k, v]) => `- ${k}: ${v}`)
          .join("\n");
        messages[0].content = `Context:\n${contextStr}\n\nRequest: ${userInput}`;
      }

      const result = await modelRouter.generate(
        messages,
        this._getTaskType(),
        "normal",
        "balanced",
        "normal",
        this.agentType,
        this.systemPrompt,
      );

      task.result = result;
      task.status = "completed";
      task.completedAt = new Date().toISOString();

      return result;
    } catch (e) {
      task.status = "failed";
      task.result = String(e);
      console.error(`Agent ${this.name} task failed: ${e}`);
      return `Error: ${e}`;
    } finally {
      this.status = AgentStatus.IDLE;
      this.currentTask = null;
      this.taskHistory.push(task);

      await eventBus.emit("agent_status_change", this.name, {
        agent: this.name,
        status: "idle",
      });
    }
  }

  async *processStream(
    userInput: string,
    context?: Record<string, unknown>,
  ): AsyncGenerator<string> {
    this.status = AgentStatus.ACTIVE;
    const messages: Array<{ role: string; content: string }> = [
      { role: "user", content: userInput },
    ];

    if (context) {
      const contextStr = Object.entries(context)
        .map(([k, v]) => `- ${k}: ${v}`)
        .join("\n");
      messages[0].content = `Context:\n${contextStr}\n\nRequest: ${userInput}`;
    }

    try {
      yield* modelRouter.generateStream(
        messages,
        this._getTaskType(),
        "normal",
        "balanced",
        "normal",
        this.agentType,
        this.systemPrompt,
      );
    } finally {
      this.status = AgentStatus.IDLE;
    }
  }

  private _getTaskType(): string {
    const mapping: Partial<Record<AgentType, string>> = {
      [AgentType.CODER]: "coding",
      [AgentType.ARCHITECT]: "architecture",
      [AgentType.REVIEWER]: "review",
      [AgentType.DEBUGGER]: "debug",
      [AgentType.RESEARCHER]: "research",
      [AgentType.DOCUMENTATION]: "documentation",
      [AgentType.AUTOMATION]: "automation",
    };
    return mapping[this.agentType] ?? "chat";
  }

  getStatus(): Record<string, unknown> {
    return {
      name: this.name,
      type: this.agentType,
      status: this.status,
      route: this.defaultRoute,
      current_task: this.currentTask?.description ?? null,
      tasks_completed: this.taskHistory.length,
      created_at: this.createdAt,
    };
  }
}
