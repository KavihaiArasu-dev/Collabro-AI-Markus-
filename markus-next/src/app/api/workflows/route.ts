/**
 * Markus AI — Workflows API
 */

import { NextRequest, NextResponse } from "next/server";
import { workflowEngine } from "@/lib/workflows/workflow-engine";

export async function GET() {
  return NextResponse.json({ workflows: workflowEngine.listWorkflows() });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { name, description, steps, trigger_type } = body;

  if (!name) {
    return NextResponse.json({ error: "name is required" }, { status: 400 });
  }

  const workflow = workflowEngine.createWorkflow(
    name,
    description || "",
    steps || [],
    trigger_type || "manual",
  );

  return NextResponse.json({
    status: "created",
    workflow: {
      id: workflow.id,
      name: workflow.name,
      steps_count: workflow.steps.length,
    },
  });
}
