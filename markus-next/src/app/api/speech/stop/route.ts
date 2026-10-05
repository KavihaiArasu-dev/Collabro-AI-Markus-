/**
 * Markus AI — Speech Stop API Route
 * POST /api/speech/stop
 */

import { NextResponse } from "next/server";

export async function POST() {
  return NextResponse.json({ success: true });
}
