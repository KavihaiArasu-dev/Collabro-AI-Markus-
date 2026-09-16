/**
 * Markus AI — Plugins API
 */

import { NextResponse } from "next/server";
import { pluginManager } from "@/lib/plugins/plugin-manager";

export async function GET() {
  return NextResponse.json({ plugins: pluginManager.listPlugins() });
}
