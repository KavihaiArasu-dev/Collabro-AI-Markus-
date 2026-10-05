/**
 * Markus AI — Delete Known Face API Route
 * DELETE /api/vision/known-faces/[name]
 */

import { NextRequest, NextResponse } from "next/server";
import { visionService } from "@/lib/vision/vision-service";

export async function DELETE(
  _request: NextRequest,
  context: { params: Promise<{ name: string }> }
) {
  try {
    const { name } = await context.params;
    const decodedName = decodeURIComponent(name || "");
    const success = visionService.deleteFace(decodedName);
    return NextResponse.json({
      success,
      deleted: decodedName,
      known_faces: visionService.getKnownFaces(),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Error deleting face";
    return NextResponse.json({ success: false, error: errorMsg }, { status: 400 });
  }
}
