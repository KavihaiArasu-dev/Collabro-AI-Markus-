/**
 * Markus AI — Speech Speak API Route
 * POST /api/speech/speak
 */

import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const text = body.text || "";
    return NextResponse.json({
      success: true,
      text,
      audio_base64: null, // Instructs browser fallback to use native speech synthesis
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Error processing speech";
    return NextResponse.json({ success: false, error: errorMsg }, { status: 500 });
  }
}
