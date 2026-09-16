/**
 * Markus AI — System API Routes
 * Port of /api/system/* from FastAPI.
 */

import { NextResponse } from "next/server";
import { toolRouter } from "@/lib/tools/tool-router";

export async function GET() {
  const result = await toolRouter.execute("system_info", {});
  return NextResponse.json(result.result ?? result);
}
