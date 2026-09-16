/**
 * Markus AI — Health API Route
 * Port of /api/health from FastAPI.
 */

import { NextResponse } from "next/server";
import { omnirouteClient } from "@/lib/ai/omniroute-client";

export async function GET() {
  return NextResponse.json({
    status: "online",
    service: "Markus AI (Next.js)",
    version: "2.0.0",
    provider: omnirouteClient.activeProvider,
    model: omnirouteClient.activeModel,
    connected: omnirouteClient.isConnected,
  });
}
