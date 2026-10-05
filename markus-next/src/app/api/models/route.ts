/**
 * Markus AI — Models API Routes
 */

import { NextResponse } from "next/server";
import { modelRouter } from "@/lib/core/model-router";
import { modelRegistry } from "@/lib/ai/model-registry";
import { routingPolicy } from "@/lib/ai/routing-policy";

export async function GET() {
  const status = await modelRouter.checkGatewayStatus();
  return NextResponse.json({
    gateway: status,
    profiles: modelRegistry.listProfiles(),
    tiers: routingPolicy.getTierInfo(),
  });
}
