/**
 * Markus AI — Workflow Engine & Builder (§8, §14)
 * Direct port from workflows/workflow_engine.py.
 */

import { v4 as uuidv4 } from "uuid";

export enum TriggerType {
  MANUAL = "manual",
  SCHEDULE = "schedule",
  WEBHOOK = "webhook",
  EVENT = "event",
}

export enum StepStatus {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  SKIPPED = "skipped",
}

interface WorkflowStep {
  id: string;
  name: string;
  agent: string;
  tool: string | null;
  arguments: Record<string, unknown>;
  condition: string | null;
  status: StepStatus;
  result: unknown;
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  triggerType: TriggerType;
  triggerConfig: Record<string, unknown>;
  steps: WorkflowStep[];
  createdAt: string;
  isActive: boolean;
}

class WorkflowEngine {
  private _workflows: Map<string, Workflow> = new Map();

  constructor() {
    this._seedDefaultWorkflows();
    console.log("Workflow Engine initialized");
  }

  private _seedDefaultWorkflows(): void {
    const ciWorkflow: Workflow = {
      id: uuidv4().slice(0, 8),
      name: "CI/CD Review & Test",
      description: "Runs code review, checks git status, and runs unit tests",
      triggerType: TriggerType.MANUAL,
      triggerConfig: {},
      steps: [
        {
          id: uuidv4().slice(0, 8), name: "Git Status Check", agent: "automation",
          tool: "git_status", arguments: {}, condition: null, status: StepStatus.PENDING, result: null,
        },
        {
          id: uuidv4().slice(0, 8), name: "Code Review", agent: "reviewer",
          tool: null, arguments: {}, condition: null, status: StepStatus.PENDING, result: null,
        },
      ],
      createdAt: new Date().toISOString(),
      isActive: true,
    };
    this._workflows.set(ciWorkflow.id, ciWorkflow);
  }

  createWorkflow(
    name: string, description: string,
    steps: Record<string, unknown>[], triggerType: string = "manual",
  ): Workflow {
    const parsedSteps: WorkflowStep[] = steps.map((s) => ({
      id: uuidv4().slice(0, 8),
      name: (s.name as string) ?? "Unnamed Step",
      agent: (s.agent as string) ?? "orchestrator",
      tool: (s.tool as string) ?? null,
      arguments: (s.arguments as Record<string, unknown>) ?? {},
      condition: (s.condition as string) ?? null,
      status: StepStatus.PENDING,
      result: null,
    }));

    const wf: Workflow = {
      id: uuidv4().slice(0, 8),
      name,
      description,
      triggerType: triggerType as TriggerType,
      triggerConfig: {},
      steps: parsedSteps,
      createdAt: new Date().toISOString(),
      isActive: true,
    };

    this._workflows.set(wf.id, wf);
    console.log(`Workflow created: ${wf.name} (${wf.id})`);
    return wf;
  }

  listWorkflows(): Record<string, unknown>[] {
    return Array.from(this._workflows.values()).map((w) => ({
      id: w.id,
      name: w.name,
      description: w.description,
      trigger_type: w.triggerType,
      steps_count: w.steps.length,
      created_at: w.createdAt,
      is_active: w.isActive,
    }));
  }

  getWorkflow(workflowId: string): Workflow | undefined {
    return this._workflows.get(workflowId);
  }
}

export const workflowEngine = new WorkflowEngine();
