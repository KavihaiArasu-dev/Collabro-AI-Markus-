/**
 * Markus AI — Vision Frame Analysis Route
 * POST /api/vision/analyze-frame
 */

import { NextRequest, NextResponse } from "next/server";
import { visionService } from "@/lib/vision/vision-service";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const imageBase64 = body.image_base64 || body.image;
    const result = visionService.analyzeFrame(imageBase64);
    return NextResponse.json(result);
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Error analyzing frame";
    return NextResponse.json(
      {
        face_count: 0,
        faces: [],
        expression: "neutral",
        expression_confidence: 0,
        hedged_description: `Analysis bypass: ${errorMsg}`,
      },
      { status: 200 }
    );
  }
}
