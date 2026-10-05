/**
 * Markus AI — Register Face API Route
 * POST /api/vision/register-face
 */

import { NextRequest, NextResponse } from "next/server";
import { visionService } from "@/lib/vision/vision-service";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const name = body.name ? String(body.name).trim() : "";
    if (!name) {
      return NextResponse.json(
        { success: false, error: "Face name is required" },
        { status: 400 }
      );
    }

    visionService.registerFace(name);
    return NextResponse.json({
      success: true,
      name,
      known_faces: visionService.getKnownFaces(),
      message: `Profile registered for '${name}'`,
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Error registering face";
    return NextResponse.json({ success: false, error: errorMsg }, { status: 500 });
  }
}
