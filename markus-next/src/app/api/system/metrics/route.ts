/**
 * Markus AI — System Metrics API Route
 */

import { NextResponse } from "next/server";
import { toolRouter } from "@/lib/tools/tool-router";

export async function GET() {
  const result = await toolRouter.execute("system_info", {});
  return NextResponse.json(result.result ?? result);
}
