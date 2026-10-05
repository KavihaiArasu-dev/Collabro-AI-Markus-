/**
 * Markus AI — Agent Status API
 */

import { NextRequest, NextResponse } from "next/server";
import { orchestrator } from "@/lib/agents/orchestrator";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ agentType: string }> },
) {
  const { agentType } = await params;
  const status = orchestrator.getAgentStatus(agentType);
  if (!status) {
    return NextResponse.json({ error: `Agent not found: ${agentType}` }, { status: 404 });
  }
  return NextResponse.json(status);
}
