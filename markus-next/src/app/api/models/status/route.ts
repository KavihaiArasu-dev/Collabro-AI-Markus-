/**
 * Markus AI — Models Status API Route
 *
 * Supplies gateway connectivity, models, and routing info to HUD and Dashboard.
 */

import { NextResponse } from "next/server";
import { modelRouter } from "@/lib/core/model-router";
import { modelRegistry } from "@/lib/ai/model-registry";
import { routingPolicy } from "@/lib/ai/routing-policy";

export async function GET() {
  try {
    const status = await modelRouter.checkGatewayStatus();
    return NextResponse.json({
      ...status,
      profiles: modelRegistry.listProfiles(),
      tiers: routingPolicy.getTierInfo(),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json(
      {
        connected: false,
        error: errorMsg,
        available_models: [],
        model_count: 0,
        profiles: [],
        tiers: [],
      },
      { status: 200 }
    );
  }
}
