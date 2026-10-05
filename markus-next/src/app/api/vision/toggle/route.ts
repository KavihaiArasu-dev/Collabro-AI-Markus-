/**
 * Markus AI — Toggle Camera / Vision API Route
 * POST /api/vision/toggle
 */

import { NextRequest, NextResponse } from "next/server";
import { visionService } from "@/lib/vision/vision-service";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const enabled = body.enabled !== false;
    visionService.setCameraActive(enabled);
    return NextResponse.json({
      success: true,
      enabled: visionService.getCameraActive(),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Error toggling camera";
    return NextResponse.json({ success: false, error: errorMsg }, { status: 500 });
  }
}
