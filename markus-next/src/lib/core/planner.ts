/**
 * Markus AI — Planner (§10, §11a)
 *
 * Breaks complex requests into step-by-step plans before execution.
 * Direct port from core/planner.py.
 */

import { v4 as uuidv4 } from "uuid";

export enum PlanStepStatus {
  PENDING = "pending",
  IN_PROGRESS = "in_progress",
  WAITING_APPROVAL = "waiting_approval",
  COMPLETED = "completed",
  FAILED = "failed",
  SKIPPED = "skipped",
}

export interface PlanStep {
  id: string;
  description: string;
  agentType: string;
  toolName: string | null;
  toolArguments: Record<string, unknown>;
  riskLevel: string;
  status: PlanStepStatus;
  result: string | null;
  error: string | null;
  verified: boolean;
  verificationDetails: Record<string, unknown> | null;
  startedAt: string | null;
  completedAt: string | null;
}

export interface ExecutionPlan {
  id: string;
  goal: string;
  steps: PlanStep[];
  status: string;
  createdAt: string;
  completedAt: string | null;
  currentStepIndex: number;
}

class Planner {
  private _activePlans: Map<string, ExecutionPlan> = new Map();

  constructor() {
    console.log("Planner initialized");
  }

  createPlan(goal: string, steps: Record<string, unknown>[]): ExecutionPlan {
    const planSteps: PlanStep[] = steps.map((s) => ({
      id: uuidv4().slice(0, 8),
      description: (s.description as string) ?? "",
      agentType: (s.agent_type as string) ?? "orchestrator",
      toolName: (s.tool_name as string) ?? null,
      toolArguments: (s.tool_arguments as Record<string, unknown>) ?? {},
      riskLevel: (s.risk_level as string) ?? "low",
      status: PlanStepStatus.PENDING,
      result: null,
      error: null,
      verified: false,
      verificationDetails: null,
      startedAt: null,
      completedAt: null,
    }));

    const plan: ExecutionPlan = {
      id: uuidv4().slice(0, 8),
      goal,
      steps: planSteps,
      status: "created",
      createdAt: new Date().toISOString(),
      completedAt: null,
      currentStepIndex: 0,
    };

    this._activePlans.set(plan.id, plan);
    console.log(`Plan created: ${plan.id} — ${goal} (${planSteps.length} steps)`);
    return plan;
  }

  createSimplePlan(goal: string, agentType: string = "orchestrator"): ExecutionPlan {
    return this.createPlan(goal, [{ description: goal, agent_type: agentType, risk_level: "low" }]);
  }

  advanceStep(
    planId: string,
    result?: string,
    verified: boolean = true,
    verificationDetails?: Record<string, unknown>,
  ): PlanStep | null {
    const plan = this._activePlans.get(planId);
    if (!plan || plan.currentStepIndex >= plan.steps.length) return null;

    const current = plan.steps[plan.currentStepIndex];
    current.status = PlanStepStatus.COMPLETED;
    current.result = result ?? null;
    current.verified = verified;
    current.verificationDetails = verificationDetails ?? null;
    current.completedAt = new Date().toISOString();

    plan.currentStepIndex++;

    const isComplete = plan.steps.every(
      (s) => s.status === PlanStepStatus.COMPLETED || s.status === PlanStepStatus.SKIPPED,
    );

    if (isComplete) {
      plan.status = "completed";
      plan.completedAt = new Date().toISOString();
      console.log(`Plan ${planId} completed`);
      return null;
    }

    const nextStep = plan.steps[plan.currentStepIndex];
    if (nextStep) {
      nextStep.status = PlanStepStatus.IN_PROGRESS;
      nextStep.startedAt = new Date().toISOString();
    }

    return nextStep ?? null;
  }

  failStep(planId: string, error: string): void {
    const plan = this._activePlans.get(planId);
    if (plan && plan.currentStepIndex < plan.steps.length) {
      const current = plan.steps[plan.currentStepIndex];
      current.status = PlanStepStatus.FAILED;
      current.error = error;
      plan.status = "failed";
      console.error(`Plan ${planId} step failed: ${error}`);
    }
  }

  getPlan(planId: string): ExecutionPlan | undefined {
    return this._activePlans.get(planId);
  }

  listActivePlans(): ExecutionPlan[] {
    return Array.from(this._activePlans.values()).filter(
      (p) => p.status !== "completed" && p.status !== "failed",
    );
  }

  cleanupCompleted(): void {
    const toRemove: string[] = [];
    for (const [pid, plan] of this._activePlans) {
      if (plan.status === "completed" || plan.status === "failed") {
        toRemove.push(pid);
      }
    }
    for (const pid of toRemove) {
      this._activePlans.delete(pid);
    }
  }
}

// Singleton
export const planner = new Planner();
