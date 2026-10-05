/**
 * Markus AI — Known Faces API Route
 * GET /api/vision/known-faces
 */

import { NextResponse } from "next/server";
import { visionService } from "@/lib/vision/vision-service";

export async function GET() {
  const faces = visionService.getKnownFaces();
  return NextResponse.json({
    known_faces: faces,
    count: faces.length,
  });
}
