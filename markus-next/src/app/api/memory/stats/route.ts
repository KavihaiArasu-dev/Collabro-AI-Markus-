/**
 * Markus AI — Memory Stats API
 */

import { NextResponse } from "next/server";
import { memoryManager } from "@/lib/memory/memory-manager";

export async function GET() {
  return NextResponse.json(memoryManager.getStats());
}
