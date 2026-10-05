/**
 * Markus AI — Vision Service
 *
 * Handles facial profile persistence, camera perception state,
 * and frame analysis metadata for the PerceptionWidget HUD.
 */

import fs from "fs";
import path from "path";

export interface FaceItem {
  track_id: number;
  identity: string;
  expression: string;
  expression_confidence: number;
  normalized_bbox: { x: number; y: number; w: number; h: number };
}

export interface FrameAnalysisResult {
  face_count: number;
  faces: FaceItem[];
  expression: string;
  expression_confidence: number;
  hedged_description: string;
}

class VisionService {
  private knownFaces: Set<string> = new Set(["Kavihai Arasu (Owner)"]);
  private storagePath: string;
  private isCameraActive: boolean = true;

  constructor() {
    this.storagePath = path.resolve(process.cwd(), "data", "known_faces.json");
    this.loadFaces();
  }

  private loadFaces() {
    try {
      if (fs.existsSync(this.storagePath)) {
        const raw = fs.readFileSync(this.storagePath, "utf-8");
        const list = JSON.parse(raw);
        if (Array.isArray(list)) {
          list.forEach((f) => {
            if (typeof f === "string" && f.trim()) {
              this.knownFaces.add(f.trim());
            }
          });
        }
      }
    } catch (err) {
      console.warn("VisionService: Failed to load faces from disk", err);
    }
  }

  private saveFaces() {
    try {
      const dir = path.dirname(this.storagePath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      fs.writeFileSync(
        this.storagePath,
        JSON.stringify(Array.from(this.knownFaces), null, 2),
        "utf-8"
      );
    } catch (err) {
      console.warn("VisionService: Failed to save faces to disk", err);
    }
  }

  public getKnownFaces(): string[] {
    return Array.from(this.knownFaces);
  }

  public registerFace(name: string): boolean {
    const trimmed = name.trim();
    if (!trimmed) return false;
    this.knownFaces.add(trimmed);
    this.saveFaces();
    return true;
  }

  public deleteFace(name: string): boolean {
    const trimmed = name.trim();
    if (this.knownFaces.has(trimmed)) {
      this.knownFaces.delete(trimmed);
      if (this.knownFaces.size === 0) {
        this.knownFaces.add("Kavihai Arasu (Owner)");
      }
      this.saveFaces();
      return true;
    }
    return false;
  }

  public setCameraActive(enabled: boolean) {
    this.isCameraActive = enabled;
  }

  public getCameraActive(): boolean {
    return this.isCameraActive;
  }

  public analyzeFrame(imageBase64?: string): FrameAnalysisResult {
    if (!imageBase64 || imageBase64.length < 50) {
      return {
        face_count: 0,
        faces: [],
        expression: "neutral",
        expression_confidence: 0,
        hedged_description: "No optical frame received.",
      };
    }

    const primaryIdentity = this.knownFaces.has("Kavihai Arasu (Owner)")
      ? "Kavihai Arasu (Owner)"
      : Array.from(this.knownFaces)[0] || "User";

    return {
      face_count: 1,
      faces: [
        {
          track_id: 1,
          identity: primaryIdentity,
          expression: "neutral",
          expression_confidence: 0.91,
          normalized_bbox: {
            x: 0.25,
            y: 0.15,
            w: 0.5,
            h: 0.6,
          },
        },
      ],
      expression: "neutral",
      expression_confidence: 0.91,
      hedged_description: `${primaryIdentity} recognized. Attention engaged.`,
    };
  }
}

export const visionService = new VisionService();
