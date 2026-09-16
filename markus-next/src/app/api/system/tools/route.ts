/**
 * Markus AI — System Tools API
 */

import { NextRequest, NextResponse } from "next/server";
import { toolRouter } from "@/lib/tools/tool-router";

export async function GET() {
  return NextResponse.json({ tools: toolRouter.listTools() });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { tool_name, toolName, arguments: args = {}, args: altArgs = {} } = body;
    const name = tool_name || toolName;
    const toolArgs = { ...altArgs, ...args, ...(body.command ? { command: body.command } : {}), ...(body.app_name ? { app_name: body.app_name } : {}), ...(body.url ? { url: body.url } : {}), ...(body.query ? { query: body.query } : {}) };

    if (!name) {
      return NextResponse.json({ success: false, error: "tool_name is required" }, { status: 400 });
    }

    const result = await toolRouter.execute(name, toolArgs);
    return NextResponse.json(result);
  } catch (e) {
    return NextResponse.json({ success: false, error: String(e) }, { status: 500 });
  }
}

