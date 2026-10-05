/**
 * Markus AI — Agents API Routes
 */

import { NextResponse } from "next/server";
import { orchestrator } from "@/lib/agents/orchestrator";

export async function GET() {
  return NextResponse.json({ agents: orchestrator.listAgents() });
}
