/**
 * Markus AI — Agents API Routes
 * Port of /api/agents from FastAPI.
 */

import { NextResponse } from "next/server";
import { orchestrator } from "@/lib/agents/orchestrator";

export async function GET() {
  return NextResponse.json({ agents: orchestrator.listAgents() });
}
