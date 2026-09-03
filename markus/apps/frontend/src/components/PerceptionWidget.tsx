import React, { useState, useEffect, useRef } from 'react';
import { Camera, CameraOff, Eye, ShieldCheck, Activity, Smile, Sparkles, UserCheck, UserPlus, Check, X, Trash2 } from 'lucide-react';
import { useAIState } from '../context/AIStateContext';

/* ═══════════════════════════════════════════════════════════
   PERCEPTION HUD — Real-Time Face Recognition & Emotion HUD
   
   Features:
   - Live Webcam capture with hardware-accelerated video rendering
   - Multi-Face detection and real-time facial emotion recognition
   - Face Recognition & Identity Profile Registration ("Remember Face")
   - Smooth EMA (Exponential Moving Average) targeting reticle
   - Anti-flicker temporal hysteresis for facial expressions
   - Zero-layout-shift UI (stable dimensions)
   - Hedged confidence output & prompt summary
   ═══════════════════════════════════════════════════════════ */

interface PerceptionHUDProps {
  onEmotionChange?: (emotion: string, confidence: number) => void;
}

const EMOTION_META: Record<string, { label: string; emoji: string; color: string }> = {
  neutral: { label: 'Neutral / Focused', emoji: '😐', color: '#00E5FF' },
  happy: { label: 'Happy / Engaged', emoji: '😊', color: '#10B981' },
  surprised: { label: 'Surprised / Curious', emoji: '😲', color: '#FACC15' },
  sad: { label: 'Sad / Distracted', emoji: '😔', color: '#3B82F6' },
  angry: { label: 'Frustrated / Urgent', emoji: '😠', color: '#EF4444' },
  fearful: { label: 'Concerned / Alert', emoji: '😨', color: '#8B5CF6' },
  disgusted: { label: 'Displeased', emoji: '🤢', color: '#FF8A00' },
};

interface TrackedFaceItem {
  trackId: number;
  label: string;
  identity?: string;
  expression: string;
  confidence: number;
  box: { x: number; y: number; width: number; height: number };
}

export default function PerceptionWidget({ onEmotionChange }: PerceptionHUDProps) {
  const [cameraActive, setCameraActive] = useState(false);
  const [emotionActive] = useState(true);
  const [faceCount, setFaceCount] = useState(0);
  const [expression, setExpression] = useState('neutral');
  const [confidence, setConfidence] = useState(0.85);
  const [hedgedText, setHedgedText] = useState('Camera offline. Click ENABLE CAM to track expressions.');
  const [faces, setFaces] = useState<TrackedFaceItem[]>([]);
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [registerName, setRegisterName] = useState('Kavihai Arasu (Owner)');
  const [registerSuccessMsg, setRegisterSuccessMsg] = useState('');
  const [registeredFaces, setRegisteredFaces] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('markus_known_faces');
      return saved ? JSON.parse(saved) : ['Kavihai Arasu (Owner)'];
    } catch {
      return ['Kavihai Arasu (Owner)'];
    }
  });
  const [faceProfiles, setFaceProfiles] = useState<{ name: string; embedding: number[] }[]>(() => {
    try {
      const saved = localStorage.getItem('markus_known_face_profiles');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [availableCameras, setAvailableCameras] = useState<{ deviceId: string; label: string }[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string>('');
  const [emotionScores, setEmotionScores] = useState<Record<string, number>>({
    neutral: 0.85,
    happy: 0.05,
    surprised: 0.03,
    sad: 0.02,
    angry: 0.02,
    fearful: 0.02,
    disgusted: 0.01,
  });

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<any>(null);
  const backendTimerRef = useRef<any>(null);

  // Smoothing references to eliminate frame jitter
  const smoothedBoxRef = useRef<{ x: number; y: number; width: number; height: number } | null>(null);
  const consecutiveMissesRef = useRef<number>(0);
  const recentEmotionsRef = useRef<string[]>([]);
  const lastEmittedEmotionRef = useRef<string>('neutral');
  const candidateEmotionRef = useRef<{ emotion: string; firstSeen: number }>({ emotion: 'neutral', firstSeen: 0 });
  const backendAvailableRef = useRef<boolean>(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const lastBackendSuccessRef = useRef<number>(0);
  const mpDetectorRef = useRef<any>(null);
  const mpLoadingRef = useRef<boolean>(false);
  const lastDetectedNormBoxRef = useRef<{ x: number; y: number; w: number; h: number } | null>(null);

  // Exact projection of normalized bounding box over CSS object-fit: cover and scaleX(-1) mirror
  const computeVideoCoverRect = (
    nx: number,
    ny: number,
    nw: number,
    nh: number,
    vWidth: number,
    vHeight: number,
    cWidth: number,
    cHeight: number,
    mirrored: boolean = true
  ) => {
    if (!vWidth || !vHeight || !cWidth || !cHeight) {
      const rawX = mirrored ? (1 - (nx + nw)) * 100 : nx * 100;
      return {
        x: Math.max(0, Math.min(95, rawX)),
        y: Math.max(0, Math.min(95, ny * 100)),
        width: Math.max(8, Math.min(90, nw * 100)),
        height: Math.max(10, Math.min(90, nh * 100)),
      };
    }

    const vRatio = vWidth / vHeight;
    const cRatio = cWidth / cHeight;

    let renderW: number;
    let renderH: number;
    let offsetX: number;
    let offsetY: number;

    if (cRatio > vRatio) {
      renderW = cWidth;
      renderH = cWidth / vRatio;
      offsetX = 0;
      offsetY = (renderH - cHeight) / 2;
    } else {
      renderH = cHeight;
      renderW = cHeight * vRatio;
      offsetX = (renderW - cWidth) / 2;
      offsetY = 0;
    }

    let faceLeftInRender = nx * renderW;
    const faceTopInRender = ny * renderH;
    const faceWInRender = nw * renderW;
    const faceHInRender = nh * renderH;

    if (mirrored) {
      faceLeftInRender = renderW - (faceLeftInRender + faceWInRender);
    }

    const leftPct = ((faceLeftInRender - offsetX) / cWidth) * 100;
    const topPct = ((faceTopInRender - offsetY) / cHeight) * 100;
    const widthPct = (faceWInRender / cWidth) * 100;
    const heightPct = (faceHInRender / cHeight) * 100;

    return {
      x: Math.round(Math.max(0, Math.min(96, leftPct)) * 10) / 10,
      y: Math.round(Math.max(0, Math.min(96, topPct)) * 10) / 10,
      width: Math.round(Math.max(8, Math.min(95, widthPct)) * 10) / 10,
      height: Math.round(Math.max(10, Math.min(95, heightPct)) * 10) / 10,
    };
  };

  // Extract 64-dimensional normalized spatial feature embedding from cropped face region
  const extractClientFaceSignature = (
    data: Uint8ClampedArray,
    canvasW: number,
    canvasH: number,
    fx: number,
    fy: number,
    fw: number,
    fh: number
  ): number[] | null => {
    try {
      if (fw < 8 || fh < 8) return null;
      const features: number[] = [];
      const blockW = fw / 8;
      const blockH = fh / 8;

      for (let by = 0; by < 8; by++) {
        for (let bx = 0; bx < 8; bx++) {
          const startX = Math.floor(fx + bx * blockW);
          const startY = Math.floor(fy + by * blockH);
          const endX = Math.floor(fx + (bx + 1) * blockW);
          const endY = Math.floor(fy + (by + 1) * blockH);

          let sumLum = 0;
          let count = 0;
          for (let py = startY; py < endY; py += 2) {
            for (let px = startX; px < endX; px += 2) {
              if (px >= 0 && px < canvasW && py >= 0 && py < canvasH) {
                const idx = (py * canvasW + px) * 4;
                const lum = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
                sumLum += lum;
                count++;
              }
            }
          }
          const avg = count > 0 ? sumLum / count / 255.0 : 0.5;
          features.push(avg);
        }
      }

      // L2 Normalize
      const norm = Math.sqrt(features.reduce((acc, v) => acc + v * v, 0)) || 1;
      return features.map(v => v / norm);
    } catch {
      return null;
    }
  };

  // Match live face signature against registered profiles
  const matchClientFace = (
    embedding: number[] | null,
    profiles: { name: string; embedding: number[] }[]
  ): { name: string; confidence: number; isKnown: boolean } => {
    if (!profiles || profiles.length === 0 || !embedding) {
      return { name: 'Unknown', confidence: 0.85, isKnown: false };
    }

    let bestName = 'Unknown';
    let bestSim = -1;

    for (const p of profiles) {
      if (!p.embedding || p.embedding.length !== embedding.length) continue;
      let dot = 0;
      for (let i = 0; i < embedding.length; i++) {
        dot += embedding[i] * p.embedding[i];
      }
      if (dot > bestSim) {
        bestSim = dot;
        bestName = p.name;
      }
    }

    if (bestSim >= 0.72) {
      const conf = Math.min(0.98, Math.max(0.80, bestSim));
      return { name: bestName, confidence: conf, isKnown: true };
    }

    return { name: 'Unknown', confidence: 0.85, isKnown: false };
  };

  // Initialize MediaPipe Vision Tasks FaceDetector (BlazeFace Short Range)
  useEffect(() => {
    let isMounted = true;
    const initMediaPipeDetector = async () => {
      if (mpDetectorRef.current || mpLoadingRef.current) return;
      mpLoadingRef.current = true;
      try {
        const { FaceDetector, FilesetResolver } = await import('@mediapipe/tasks-vision');
        let vision: any = null;
        try {
          vision = await FilesetResolver.forVisionTasks('/wasm');
        } catch {
          vision = await FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.17/wasm');
        }

        let detector: any = null;
        try {
          detector = await FaceDetector.createFromOptions(vision, {
            baseOptions: {
              modelAssetPath: '/blaze_face_short_range.tflite',
              delegate: 'GPU',
            },
            runningMode: 'VIDEO',
            minDetectionConfidence: 0.35,
          });
        } catch {
          try {
            detector = await FaceDetector.createFromOptions(vision, {
              baseOptions: {
                modelAssetPath: '/blaze_face_short_range.tflite',
                delegate: 'CPU',
              },
              runningMode: 'VIDEO',
              minDetectionConfidence: 0.35,
            });
          } catch {
            detector = await FaceDetector.createFromOptions(vision, {
              baseOptions: {
                modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite',
                delegate: 'CPU',
              },
              runningMode: 'VIDEO',
              minDetectionConfidence: 0.35,
            });
          }
        }

        if (isMounted && detector) {
          mpDetectorRef.current = detector;
        }
      } catch (err) {
        console.warn('MediaPipe initialization fallback notice:', err);
      } finally {
        mpLoadingRef.current = false;
      }
    };

    initMediaPipeDetector();

    return () => {
      isMounted = false;
      if (mpDetectorRef.current) {
        try {
          mpDetectorRef.current.close();
        } catch {}
        mpDetectorRef.current = null;
      }
    };
  }, []);

  // Client-side real-time multi-face & biometric expression detector
  const analyzeClientSideFrame = async (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    try {
      // If backend is active and producing live detections, let backend control the overlays
      if (backendAvailableRef.current && (Date.now() - lastBackendSuccessRef.current < 1500)) {
        return;
      }

      const cRect = containerRef.current?.getBoundingClientRect();
      const cWidth = cRect?.width || 320;
      const cHeight = cRect?.height || 190;

      // ── Tier 1: MediaPipe BlazeFace Deep Learning Detector (Pinpoint Accurate & Fast) ──
      if (mpDetectorRef.current && videoRef.current && videoRef.current.readyState >= 2) {
        try {
          const mpResult = mpDetectorRef.current.detectForVideo(videoRef.current, performance.now());
          const detectedFaces = mpResult?.detections;

          if (detectedFaces && detectedFaces.length > 0) {
            const vw = videoRef.current.videoWidth || width;
            const vh = videoRef.current.videoHeight || height;

            const trackedFaces: TrackedFaceItem[] = [];
            let primaryScores: Record<string, number> | undefined = undefined;

            for (let i = 0; i < detectedFaces.length; i++) {
              const face = detectedFaces[i];
              const bbox = face.boundingBox;
              if (!bbox || bbox.width <= 0 || bbox.height <= 0) continue;

              const normX = Math.max(0, Math.min(0.95, bbox.originX / vw));
              const normY = Math.max(0, Math.min(0.95, bbox.originY / vh));
              const normW = Math.max(0.05, Math.min(1 - normX, bbox.width / vw));
              const normH = Math.max(0.05, Math.min(1 - normY, bbox.height / vh));

              if (i === 0) {
                lastDetectedNormBoxRef.current = { x: normX, y: normY, w: normW, h: normH };
              }

              const coverBox = computeVideoCoverRect(normX, normY, normW, normH, vw, vh, cWidth, cHeight, true);

              // Apply EMA smoothing to eliminate jitter while following movements
              let finalBox = coverBox;
              if (i === 0) {
                if (smoothedBoxRef.current) {
                  const dx = Math.abs(smoothedBoxRef.current.x - coverBox.x);
                  const dy = Math.abs(smoothedBoxRef.current.y - coverBox.y);
                  const alpha = (dx > 18 || dy > 18) ? 0.80 : 0.45;
                  smoothedBoxRef.current = {
                    x: smoothedBoxRef.current.x * (1 - alpha) + coverBox.x * alpha,
                    y: smoothedBoxRef.current.y * (1 - alpha) + coverBox.y * alpha,
                    width: smoothedBoxRef.current.width * (1 - alpha) + coverBox.width * alpha,
                    height: smoothedBoxRef.current.height * (1 - alpha) + coverBox.height * alpha,
                  };
                } else {
                  smoothedBoxRef.current = { ...coverBox };
                }

                finalBox = {
                  x: Math.round(smoothedBoxRef.current.x * 10) / 10,
                  y: Math.round(smoothedBoxRef.current.y * 10) / 10,
                  width: Math.round(smoothedBoxRef.current.width * 10) / 10,
                  height: Math.round(smoothedBoxRef.current.height * 10) / 10,
                };
              }

              // Crop face region for expression analysis
              const cropX = Math.max(0, Math.floor(normX * width));
              const cropY = Math.max(0, Math.floor(normY * height));
              const cropW = Math.min(width - cropX, Math.floor(normW * width));
              const cropH = Math.min(height - cropY, Math.floor(normH * height));

              let rawEmotion = 'neutral';
              let rawConf = face.categories?.[0]?.score || 0.94;

              if (cropW > 8 && cropH > 8) {
                const faceImgData = ctx.getImageData(cropX, cropY, cropW, cropH);
                const { emotion, conf, scores } = estimateExpressionFromImageData(
                  faceImgData.data,
                  cropW,
                  cropH,
                  0,
                  0,
                  cropW,
                  cropH
                );
                rawEmotion = emotion;
                rawConf = Math.min(0.98, Math.max(0.85, (face.categories?.[0]?.score || 0.90) * 0.4 + conf * 0.6));
                if (i === 0) primaryScores = scores;
              }

              // Live biometric signature recognition
              const liveSignature = extractClientFaceSignature(
                ctx.getImageData(0, 0, width, height).data,
                width,
                height,
                cropX,
                cropY,
                cropW,
                cropH
              );

              // Auto-seed owner baseline on initial load if no profile exists yet
              if (faceProfiles.length === 0 && liveSignature && liveSignature.length > 0 && i === 0) {
                const initialOwner = registeredFaces[0] || 'Kavihai Arasu (Owner)';
                const initialProf = [{ name: initialOwner, embedding: liveSignature }];
                setFaceProfiles(initialProf);
                try {
                  localStorage.setItem('markus_known_face_profiles', JSON.stringify(initialProf));
                } catch {}
              }

              const recognized = matchClientFace(liveSignature, faceProfiles);
              const isKnown = recognized.isKnown;
              const identityName = isKnown ? recognized.name : 'Unknown';
              const displayLabel = isKnown ? recognized.name : (i === 0 ? 'Unknown' : `Unknown (#${i + 1})`);

              trackedFaces.push({
                trackId: i + 1,
                identity: identityName,
                label: displayLabel,
                expression: rawEmotion,
                confidence: roundDec(Math.max(rawConf, recognized.confidence), 2),
                box: finalBox,
              });
            }

            if (trackedFaces.length > 0) {
              return applyDetectedFaces(trackedFaces, primaryScores);
            }
          }
        } catch (mpErr) {
          console.warn('MediaPipe detection frame notice:', mpErr);
        }
      }

      // ── Tier 2: Native Browser Hardware-Accelerated Multi-FaceDetector API (if supported) ──
      if (typeof (window as any).FaceDetector === 'function' && videoRef.current) {
        try {
          const detector = new (window as any).FaceDetector({ fastMode: true, maxDetectedFaces: 10 });
          const detectedNativeFaces = await detector.detect(videoRef.current);

          if (detectedNativeFaces && detectedNativeFaces.length > 0) {
            const vw = videoRef.current.videoWidth || width;
            const vh = videoRef.current.videoHeight || height;

            const trackedFaces: TrackedFaceItem[] = [];
            let primaryScores: Record<string, number> | undefined = undefined;

            for (let i = 0; i < detectedNativeFaces.length; i++) {
              const face = detectedNativeFaces[i];
              const box = face.boundingBox;

              const normX = Math.max(0, Math.min(0.95, box.x / vw));
              const normY = Math.max(0, Math.min(0.95, box.y / vh));
              const normW = Math.max(0.05, Math.min(1 - normX, box.width / vw));
              const normH = Math.max(0.05, Math.min(1 - normY, box.height / vh));

              if (i === 0) {
                lastDetectedNormBoxRef.current = { x: normX, y: normY, w: normW, h: normH };
              }

              const coverBox = computeVideoCoverRect(normX, normY, normW, normH, vw, vh, cWidth, cHeight, true);

              let finalBox = coverBox;
              if (i === 0) {
                if (smoothedBoxRef.current) {
                  const dx = Math.abs(smoothedBoxRef.current.x - coverBox.x);
                  const dy = Math.abs(smoothedBoxRef.current.y - coverBox.y);
                  const alpha = (dx > 18 || dy > 18) ? 0.80 : 0.45;
                  smoothedBoxRef.current = {
                    x: smoothedBoxRef.current.x * (1 - alpha) + coverBox.x * alpha,
                    y: smoothedBoxRef.current.y * (1 - alpha) + coverBox.y * alpha,
                    width: smoothedBoxRef.current.width * (1 - alpha) + coverBox.width * alpha,
                    height: smoothedBoxRef.current.height * (1 - alpha) + coverBox.height * alpha,
                  };
                } else {
                  smoothedBoxRef.current = { ...coverBox };
                }

                finalBox = {
                  x: Math.round(smoothedBoxRef.current.x * 10) / 10,
                  y: Math.round(smoothedBoxRef.current.y * 10) / 10,
                  width: Math.round(smoothedBoxRef.current.width * 10) / 10,
                  height: Math.round(smoothedBoxRef.current.height * 10) / 10,
                };
              }

              // Crop face region for expression analysis
              const cropX = Math.max(0, Math.floor(normX * width));
              const cropY = Math.max(0, Math.floor(normY * height));
              const cropW = Math.min(width - cropX, Math.floor(normW * width));
              const cropH = Math.min(height - cropY, Math.floor(normH * height));

              let rawEmotion = 'neutral';
              let rawConf = 0.88;

              if (cropW > 8 && cropH > 8) {
                const faceImgData = ctx.getImageData(cropX, cropY, cropW, cropH);
                const { emotion, conf, scores } = estimateExpressionFromImageData(
                  faceImgData.data,
                  cropW,
                  cropH,
                  0,
                  0,
                  cropW,
                  cropH
                );
                rawEmotion = emotion;
                rawConf = conf;
                if (i === 0) primaryScores = scores;
              }

              const liveSignature = extractClientFaceSignature(
                ctx.getImageData(0, 0, width, height).data,
                width,
                height,
                cropX,
                cropY,
                cropW,
                cropH
              );
              // Auto-seed owner baseline on initial load if no profile exists yet
              if (faceProfiles.length === 0 && liveSignature && liveSignature.length > 0 && i === 0) {
                const initialOwner = registeredFaces[0] || 'Kavihai Arasu (Owner)';
                const initialProf = [{ name: initialOwner, embedding: liveSignature }];
                setFaceProfiles(initialProf);
                try {
                  localStorage.setItem('markus_known_face_profiles', JSON.stringify(initialProf));
                } catch {}
              }

              const recognized = matchClientFace(liveSignature, faceProfiles);
              const isKnown = recognized.isKnown;
              const identityName = isKnown ? recognized.name : 'Unknown';
              const displayLabel = isKnown ? recognized.name : (i === 0 ? 'Unknown' : `Unknown (#${i + 1})`);

              trackedFaces.push({
                trackId: i + 1,
                identity: identityName,
                label: displayLabel,
                expression: rawEmotion,
                confidence: roundDec(Math.max(rawConf, recognized.confidence), 2),
                box: finalBox,
              });
            }

            return applyDetectedFaces(trackedFaces, primaryScores);
          }
        } catch {}
      }

      // ── Tier 3: Robust Skin-Chroma (YCrCb + RGB) & Facial Structure Biometric Fallback ──
      const imgData = ctx.getImageData(0, 0, width, height);
      const data = imgData.data;

      // 1. Build Skin Chrominance Map with human biological RGB + YCrCb constraints
      const skinGrid = new Uint8Array(width * height);
      const lumGrid = new Float32Array(width * height);
      let skinPixelCount = 0;

      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          const idx = (y * width + x) * 4;
          const r = data[idx];
          const g = data[idx + 1];
          const b = data[idx + 2];

          // YCrCb color space conversion
          const lum = 0.299 * r + 0.587 * g + 0.114 * b;
          const cr = (r - lum) * 0.713 + 128;
          const cb = (b - lum) * 0.564 + 128;

          lumGrid[y * width + x] = lum;

          // Reject non-skin objects (white tiles, gray walls, furniture, curtains)
          // Human skin across all ethnicities requires: r > g, r > b, cr in [132, 176], cb in [78, 130]
          const isSkinChroma =
            r > g &&
            r > b &&
            (r - g) >= 3 &&
            (r - b) >= 6 &&
            cr >= 132 &&
            cr <= 176 &&
            cb >= 78 &&
            cb <= 130 &&
            lum >= 25 &&
            lum <= 235;

          if (isSkinChroma) {
            skinGrid[y * width + x] = 1;
            skinPixelCount++;
          }
        }
      }

      // Build 2D Integral Images for both Skin Density and Luminance
      const skinIntegral = new Float64Array((width + 1) * (height + 1));
      const lumIntegral = new Float64Array((width + 1) * (height + 1));

      for (let y = 0; y < height; y++) {
        let rowSkin = 0;
        let rowLum = 0;
        for (let x = 0; x < width; x++) {
          rowSkin += skinGrid[y * width + x];
          rowLum += lumGrid[y * width + x];
          const idx = (y + 1) * (width + 1) + (x + 1);
          skinIntegral[idx] = skinIntegral[y * (width + 1) + (x + 1)] + rowSkin;
          lumIntegral[idx] = lumIntegral[y * (width + 1) + (x + 1)] + rowLum;
        }
      }

      const getSkinDensity = (rx: number, ry: number, rw: number, rh: number): number => {
        const x1 = Math.max(0, Math.min(width, Math.floor(rx)));
        const y1 = Math.max(0, Math.min(height, Math.floor(ry)));
        const x2 = Math.max(0, Math.min(width, Math.floor(rx + rw)));
        const y2 = Math.max(0, Math.min(height, Math.floor(ry + rh)));
        const stride = width + 1;
        const totalSkin = skinIntegral[y2 * stride + x2] - skinIntegral[y1 * stride + x2] - skinIntegral[y2 * stride + x1] + skinIntegral[y1 * stride + x1];
        const area = Math.max(1, (x2 - x1) * (y2 - y1));
        return totalSkin / area;
      };

      const getLumAvg = (rx: number, ry: number, rw: number, rh: number): number => {
        const x1 = Math.max(0, Math.min(width, Math.floor(rx)));
        const y1 = Math.max(0, Math.min(height, Math.floor(ry)));
        const x2 = Math.max(0, Math.min(width, Math.floor(rx + rw)));
        const y2 = Math.max(0, Math.min(height, Math.floor(ry + rh)));
        const stride = width + 1;
        const totalLum = lumIntegral[y2 * stride + x2] - lumIntegral[y1 * stride + x2] - lumIntegral[y2 * stride + x1] + lumIntegral[y1 * stride + x1];
        const area = Math.max(1, (x2 - x1) * (y2 - y1));
        return totalLum / area;
      };

      // 2. Multi-Scale Biometric Face Pattern Search with Skin Prior
      let bestScore = -999;
      let bestBox = { x: width * 0.25, y: height * 0.12, w: width * 0.50, h: height * 0.65 };
      let faceFound = false;

      const scales = [
        { w: Math.floor(width * 0.32), h: Math.floor(height * 0.46) },
        { w: Math.floor(width * 0.42), h: Math.floor(height * 0.58) },
        { w: Math.floor(width * 0.52), h: Math.floor(height * 0.70) },
      ];

      for (const scale of scales) {
        const stepX = Math.max(8, Math.floor(scale.w * 0.15));
        const stepY = Math.max(8, Math.floor(scale.h * 0.15));
        const maxX = width - scale.w;
        const maxY = height - scale.h;

        for (let cy = Math.floor(height * 0.05); cy <= maxY; cy += stepY) {
          for (let cx = Math.floor(width * 0.08); cx <= maxX; cx += stepX) {
            const fw = scale.w;
            const fh = scale.h;

            const skinDensity = getSkinDensity(cx, cy, fw, fh);
            if (skinPixelCount > 300 && skinDensity < 0.22) {
              continue;
            }

            const forehead = getLumAvg(cx + fw * 0.20, cy + fh * 0.06, fw * 0.60, fh * 0.18);
            const eyeLeft = getLumAvg(cx + fw * 0.14, cy + fh * 0.26, fw * 0.32, fh * 0.20);
            const eyeRight = getLumAvg(cx + fw * 0.54, cy + fh * 0.26, fw * 0.32, fh * 0.20);
            const noseBridge = getLumAvg(cx + fw * 0.36, cy + fh * 0.28, fw * 0.28, fh * 0.32);
            const cheekLeft = getLumAvg(cx + fw * 0.10, cy + fh * 0.48, fw * 0.26, fh * 0.24);
            const cheekRight = getLumAvg(cx + fw * 0.64, cy + fh * 0.48, fw * 0.26, fh * 0.24);

            const avgEyes = (eyeLeft + eyeRight) / 2;
            const avgCheeks = (cheekLeft + cheekRight) / 2;

            const browEyeDiff = forehead - avgEyes;
            // Artificial step edge penalty: wall tile borders have huge contrast > 55
            const browScore = (browEyeDiff >= 5 && browEyeDiff <= 55)
              ? browEyeDiff * 1.0
              : (browEyeDiff > 55 ? Math.max(-60, 55 - (browEyeDiff - 55) * 2.5) : -20);

            // Nose bridge is brighter than eyes in a 3D human face
            const noseEyeDiff = Math.max(-10, Math.min(40, (noseBridge + avgCheeks) / 2 - avgEyes));
            const eyeSymmetry = 100 - Math.abs(eyeLeft - eyeRight);
            const cheekSymmetry = 100 - Math.abs(cheekLeft - cheekRight);

            // Center proximity prior (laptop webcam users sit centrally)
            const centerX = cx + fw / 2;
            const centerDist = Math.abs(centerX - width / 2) / (width / 2);
            const centerBonus = (1 - centerDist) * 35;

            const skinScore = skinDensity * 50;

            const biometricScore =
              skinScore +
              browScore +
              noseEyeDiff * 1.5 +
              (eyeSymmetry + cheekSymmetry) * 0.15 +
              centerBonus;

            if (biometricScore > bestScore) {
              bestScore = biometricScore;
              bestBox = { x: cx, y: cy, w: fw, h: fh };
              if (biometricScore >= 25 && skinDensity >= 0.25) {
                faceFound = true;
              }
            }
          }
        }
      }

      if (faceFound && bestScore >= 25) {
        consecutiveMissesRef.current = 0;

        const normW = bestBox.w / width;
        const normH = bestBox.h / height;
        const normX = bestBox.x / width;
        const normY = bestBox.y / height;

        lastDetectedNormBoxRef.current = { x: normX, y: normY, w: normW, h: normH };

        const coverBox = computeVideoCoverRect(
          normX,
          normY,
          normW,
          normH,
          videoRef.current?.videoWidth || width,
          videoRef.current?.videoHeight || height,
          cWidth,
          cHeight,
          true
        );
        const rawTargetX = coverBox.x;
        const rawTargetY = coverBox.y;
        const rawTargetW = coverBox.width;
        const rawTargetH = coverBox.height;

        // Smooth bounding box via Exponential Moving Average (EMA) to eliminate jitter
        if (smoothedBoxRef.current) {
          const dx = Math.abs(smoothedBoxRef.current.x - rawTargetX);
          const dy = Math.abs(smoothedBoxRef.current.y - rawTargetY);
          const alpha = (dx > 18 || dy > 18) ? 0.80 : 0.45;
          smoothedBoxRef.current = {
            x: smoothedBoxRef.current.x * (1 - alpha) + rawTargetX * alpha,
            y: smoothedBoxRef.current.y * (1 - alpha) + rawTargetY * alpha,
            width: smoothedBoxRef.current.width * (1 - alpha) + rawTargetW * alpha,
            height: smoothedBoxRef.current.height * (1 - alpha) + rawTargetH * alpha,
          };
        } else {
          smoothedBoxRef.current = {
            x: rawTargetX,
            y: rawTargetY,
            width: rawTargetW,
            height: rawTargetH,
          };
        }

        const boxX = Math.round(smoothedBoxRef.current.x * 10) / 10;
        const boxY = Math.round(smoothedBoxRef.current.y * 10) / 10;
        const boxWidth = Math.round(smoothedBoxRef.current.width * 10) / 10;
        const boxHeight = Math.round(smoothedBoxRef.current.height * 10) / 10;

        // Analyze mouth, smile, and expression geometry on face crop
        const { emotion, conf, scores } = estimateExpressionFromImageData(
          data,
          width,
          height,
          bestBox.x,
          bestBox.y,
          bestBox.w,
          bestBox.h
        );

        // Extract live biometric face embedding and recognize identity
        const liveSignature = extractClientFaceSignature(
          data,
          width,
          height,
          bestBox.x,
          bestBox.y,
          bestBox.w,
          bestBox.h
        );
        // Auto-seed owner baseline on initial load if no profile exists yet
        if (faceProfiles.length === 0 && liveSignature && liveSignature.length > 0) {
          const initialOwner = registeredFaces[0] || 'Kavihai Arasu (Owner)';
          const initialProf = [{ name: initialOwner, embedding: liveSignature }];
          setFaceProfiles(initialProf);
          try {
            localStorage.setItem('markus_known_face_profiles', JSON.stringify(initialProf));
          } catch {}
        }

        const recognized = matchClientFace(liveSignature, faceProfiles);
        const identityName = recognized.isKnown ? recognized.name : 'Unknown';

        const singleFace: TrackedFaceItem = {
          trackId: 1,
          identity: identityName,
          label: identityName,
          expression: emotion,
          confidence: roundDec(Math.max(conf, recognized.confidence), 2),
          box: {
            x: boxX,
            y: boxY,
            width: boxWidth,
            height: boxHeight,
          },
        };

        return applyDetectedFaces([singleFace], scores);
      } else {
        consecutiveMissesRef.current += 1;
        if (consecutiveMissesRef.current > 15) {
          smoothedBoxRef.current = null;
          lastDetectedNormBoxRef.current = null;
          setFaceCount(0);
          setFaces([]);
          setExpression('neutral');
          setConfidence(0);
          setEmotionScores({ neutral: 0, happy: 0, surprised: 0, sad: 0, angry: 0, fearful: 0, disgusted: 0 });
          setHedgedText('No face detected in view.');
        }
        return false;
      }
    } catch (err) {
      console.warn('Face detection pass notice:', err);
      return false;
    }
  };

  const estimateExpressionFromImageData = (
    data: Uint8ClampedArray,
    width: number,
    height: number,
    boxX: number = 0,
    boxY: number = 0,
    boxW: number = width,
    boxH: number = height,
  ): { emotion: string; conf: number; scores: Record<string, number> } => {
    // 1. Forehead / Brow & Glabella Region Analysis (top 15% to 42% of face)
    const browYStart = Math.floor(boxY + boxH * 0.16);
    const browYEnd = Math.floor(boxY + boxH * 0.42);
    const eyeXStart = Math.floor(boxX + boxW * 0.15);
    const eyeXEnd = Math.floor(boxX + boxW * 0.85);
    const glabellaXStart = Math.floor(boxX + boxW * 0.38);
    const glabellaXEnd = Math.floor(boxX + boxW * 0.62);

    let eyeBrightness = 0;
    let eyeDarkPixels = 0;
    let eyeSamples = 0;
    let glabellaBrightness = 0;
    let glabellaDarkPixels = 0;
    let glabellaSamples = 0;

    for (let ey = browYStart; ey < browYEnd; ey += 2) {
      for (let ex = eyeXStart; ex < eyeXEnd; ex += 2) {
        if (ex >= 0 && ex < width && ey >= 0 && ey < height) {
          const idx = (ey * width + ex) * 4;
          const lum = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
          eyeBrightness += lum;
          if (lum < 46) eyeDarkPixels++;
          eyeSamples++;

          if (ex >= glabellaXStart && ex <= glabellaXEnd) {
            glabellaBrightness += lum;
            if (lum < 52) glabellaDarkPixels++;
            glabellaSamples++;
          }
        }
      }
    }

    const eyeDarkRatio = eyeSamples > 0 ? eyeDarkPixels / eyeSamples : 0;
    const glabellaDarkRatio = glabellaSamples > 0 ? glabellaDarkPixels / glabellaSamples : 0;

    // 2. Cheeks Region Analysis (middle 45% to 68% of face)
    const cheekYStart = Math.floor(boxY + boxH * 0.45);
    const cheekYEnd = Math.floor(boxY + boxH * 0.68);
    let cheekBrightness = 0;
    let cheekSamples = 0;

    for (let cy = cheekYStart; cy < cheekYEnd; cy += 2) {
      for (let cx = eyeXStart; cx < eyeXEnd; cx += 2) {
        if (cx >= 0 && cx < width && cy >= 0 && cy < height) {
          const idx = (cy * width + cx) * 4;
          const lum = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
          cheekBrightness += lum;
          cheekSamples++;
        }
      }
    }
    const avgCheekLum = cheekSamples > 0 ? cheekBrightness / cheekSamples : 100;
    const avgForeheadLum = eyeSamples > 0 ? eyeBrightness / eyeSamples : 100;
    const cheekLiftContrast = avgCheekLum - avgForeheadLum;

    // 3. Mouth Region Analysis (bottom 60% to 94% of face)
    const mouthYStart = Math.floor(boxY + boxH * 0.60);
    const mouthYEnd = Math.floor(boxY + boxH * 0.94);
    const mouthXStart = Math.floor(boxX + boxW * 0.18);
    const mouthXEnd = Math.floor(boxX + boxW * 0.82);
    const mouthMidX = (mouthXStart + mouthXEnd) / 2;
    const mouthCenterW = (mouthXEnd - mouthXStart) * 0.35;

    let mouthBrightness = 0;
    let mouthDarkCavity = 0;
    let mouthSamples = 0;
    let mouthCenterLum = 0;
    let mouthCenterSamples = 0;
    let mouthCornerLum = 0;
    let mouthCornerSamples = 0;
    let brightTeethPixels = 0;

    for (let my = mouthYStart; my < mouthYEnd; my += 2) {
      for (let mx = mouthXStart; mx < mouthXEnd; mx += 2) {
        if (mx >= 0 && mx < width && my >= 0 && my < height) {
          const idx = (my * width + mx) * 4;
          const lum = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
          mouthBrightness += lum;
          if (lum < 38) mouthDarkCavity++;
          mouthSamples++;

          const isCenter = Math.abs(mx - mouthMidX) < mouthCenterW / 2;
          if (isCenter) {
            mouthCenterLum += lum;
            mouthCenterSamples++;
            if (lum > 140) brightTeethPixels++;
          } else {
            mouthCornerLum += lum;
            mouthCornerSamples++;
          }
        }
      }
    }

    const avgMouthLum = mouthSamples > 0 ? mouthBrightness / mouthSamples : 90;
    const avgCenterLum = mouthCenterSamples > 0 ? mouthCenterLum / mouthCenterSamples : 90;
    const avgCornerLum = mouthCornerSamples > 0 ? mouthCornerLum / mouthCornerSamples : 90;
    const mouthOpenRatio = mouthSamples > 0 ? mouthDarkCavity / mouthSamples : 0;
    const teethRatio = mouthCenterSamples > 0 ? brightTeethPixels / mouthCenterSamples : 0;

    // Relative Mouth Contrast: In a true smile, teeth / mouth center are noticeably brighter than corners
    const smileContrast = avgCenterLum - avgCornerLum;

    const scores: Record<string, number> = {
      neutral: 0.76,
      happy: 0.05,
      surprised: 0.04,
      sad: 0.04,
      angry: 0.04,
      fearful: 0.04,
      disgusted: 0.03,
    };

    let rawEmotion = 'neutral';
    let rawConf = 0.86;

    // ── Expression Classifier ──
    // 1. Happy / Smile: requires teeth contrast OR center brightness higher than corners + cheek lift
    if ((teethRatio > 0.12 && smileContrast > 14) || (smileContrast > 22 && cheekLiftContrast > 4)) {
      rawEmotion = 'happy';
      rawConf = Math.min(0.96, 0.76 + (teethRatio * 1.2) + (smileContrast / 100) * 0.3);
      scores.happy = roundDec(rawConf, 2);
      scores.neutral = roundDec(Math.max(0.04, 1 - rawConf), 2);
    }
    // 2. Surprised: vertical mouth cavity opening + open eyes
    else if (mouthOpenRatio > 0.18 && eyeDarkRatio > 0.18) {
      rawEmotion = 'surprised';
      rawConf = Math.min(0.94, 0.74 + mouthOpenRatio * 1.1);
      scores.surprised = roundDec(rawConf, 2);
      scores.neutral = roundDec(Math.max(0.05, 1 - rawConf), 2);
    }
    // 3. Angry / Concentrated: dark glabella furrow between brows + compressed mouth
    else if (glabellaDarkRatio > 0.30 && avgMouthLum < 75) {
      rawEmotion = 'angry';
      rawConf = Math.min(0.91, 0.72 + glabellaDarkRatio * 0.45);
      scores.angry = roundDec(rawConf, 2);
      scores.neutral = roundDec(Math.max(0.05, 1 - rawConf), 2);
    }
    // 4. Sadness: mouth corner droop (corners darker than center) + low mouth energy
    else if (avgCornerLum < avgCenterLum - 10 && avgMouthLum < 65 && cheekLiftContrast < -3) {
      rawEmotion = 'sad';
      rawConf = Math.min(0.88, 0.70 + (70 - avgMouthLum) * 0.005);
      scores.sad = roundDec(rawConf, 2);
      scores.neutral = roundDec(Math.max(0.06, 1 - rawConf), 2);
    }
    // 5. Fearful: wide eyes + moderate cavity
    else if (eyeDarkRatio > 0.32 && mouthOpenRatio > 0.08) {
      rawEmotion = 'fearful';
      rawConf = Math.min(0.88, 0.70 + eyeDarkRatio * 0.4);
      scores.fearful = roundDec(rawConf, 2);
      scores.neutral = roundDec(Math.max(0.05, 1 - rawConf), 2);
    }
    // 6. Default: Neutral resting state
    else {
      rawEmotion = 'neutral';
      rawConf = 0.88;
      scores.neutral = 0.88;
    }

    // Normalize all 7 geometric emotion scores into a true probability distribution summing to 1.0 (100%)
    const rawSum = Object.values(scores).reduce((a, b) => a + b, 0);
    const normalizedScores: Record<string, number> = {};
    for (const [k, v] of Object.entries(scores)) {
      normalizedScores[k] = roundDec(v / (rawSum || 1), 2);
    }

    return { emotion: rawEmotion, conf: rawConf, scores: normalizedScores };
  };

  const applyDetectedFaces = (
    trackedFaces: TrackedFaceItem[],
    scores?: Record<string, number>
  ) => {
    consecutiveMissesRef.current = 0;
    if (!trackedFaces || trackedFaces.length === 0) return false;

    const primaryFace = trackedFaces[0];
    const rawEmotion = primaryFace.expression;
    const rawConf = primaryFace.confidence;

    // Temporal Hysteresis for dominant label: require candidate to lead for >= 300ms before flipping
    const now = Date.now();
    if (candidateEmotionRef.current.emotion !== rawEmotion) {
      candidateEmotionRef.current = { emotion: rawEmotion, firstSeen: now };
    }
    const dwellMs = now - candidateEmotionRef.current.firstSeen;
    let stableEmotion = expression;
    if (dwellMs >= 300 || candidateEmotionRef.current.emotion === expression || expression === 'neutral') {
      stableEmotion = candidateEmotionRef.current.emotion;
    }

    primaryFace.expression = stableEmotion;

    setFaceCount(trackedFaces.length);
    setFaces(trackedFaces);
    setExpression(stableEmotion);
    setConfidence(roundDec(rawConf, 2));
    if (scores) setEmotionScores(scores);
    setHedgedText(
      trackedFaces.length > 1
        ? `Detected ${trackedFaces.length} faces in view — Primary expression: ${stableEmotion}`
        : `Visible facial expression appears ${stableEmotion} (${Math.round(rawConf * 100)}%)`
    );

    if (onEmotionChange && lastEmittedEmotionRef.current !== stableEmotion) {
      lastEmittedEmotionRef.current = stableEmotion;
      onEmotionChange(stableEmotion, rawConf);
    }
    return true;
  };

  const roundDec = (val: number, dec: number) => {
    const factor = Math.pow(10, dec);
    return Math.round(val * factor) / factor;
  };

  // Check if a device label belongs to a mobile phone, linked device, or virtual continuity camera
  const isMobileOrLinkedCamera = (label: string): boolean => {
    const lbl = (label || '').toLowerCase();
    // Never flag built-in laptop keywords as phone
    if (
      lbl.includes('integrated') ||
      lbl.includes('built-in') ||
      lbl.includes('builtin') ||
      lbl.includes('easycamera') ||
      lbl.includes('realtek') ||
      lbl.includes('chicony') ||
      lbl.includes('sunplus') ||
      lbl.includes('truevision')
    ) {
      return false;
    }

    return (
      lbl.includes('phone') ||
      lbl.includes('link to windows') ||
      lbl.includes('phone link') ||
      lbl.includes('samsung') ||
      lbl.includes('galaxy') ||
      lbl.includes('s26') ||
      lbl.includes('s25') ||
      lbl.includes('s24') ||
      lbl.includes('s23') ||
      lbl.includes('s22') ||
      lbl.includes('s21') ||
      lbl.includes('s20') ||
      lbl.includes('droidcam') ||
      lbl.includes('iriun') ||
      lbl.includes('epoccam') ||
      lbl.includes('camo') ||
      lbl.includes('ivcam') ||
      lbl.includes('continuity') ||
      lbl.includes('iphone') ||
      lbl.includes('ipad') ||
      lbl.includes('android') ||
      lbl.includes('ip webcam') ||
      lbl.includes('obs virtual') ||
      lbl.includes('virtual camera')
    );
  };

  // Check if a device label belongs to a built-in laptop webcam
  const isLaptopIntegratedCam = (label: string): boolean => {
    const lbl = (label || '').toLowerCase();
    if (isMobileOrLinkedCamera(lbl)) return false;
    return (
      lbl.includes('integrated') ||
      lbl.includes('built-in') ||
      lbl.includes('builtin') ||
      lbl.includes('internal') ||
      lbl.includes('easycamera') ||
      lbl.includes('realtek') ||
      lbl.includes('chicony') ||
      lbl.includes('sunplus') ||
      lbl.includes('sonix') ||
      lbl.includes('bison') ||
      lbl.includes('front') ||
      lbl.includes('laptop') ||
      lbl.includes('webcam') ||
      lbl.includes('hd camera') ||
      lbl.includes('truevision') ||
      lbl.includes('facetime') ||
      lbl.includes('user facing') ||
      lbl.includes('camera')
    );
  };

  // Refresh and sort video devices, prioritizing laptop webcams
  const refreshCameraDevices = async (): Promise<{ deviceId: string; label: string }[]> => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevs = devices.filter(d => d.kind === 'videoinput');

      // Sort: Laptop integrated cams first, other non-phone webcams next, phone cams last
      const sorted = [...videoDevs].sort((a, b) => {
        const aLabel = a.label || '';
        const bLabel = b.label || '';
        const aIsPhone = isMobileOrLinkedCamera(aLabel);
        const bIsPhone = isMobileOrLinkedCamera(bLabel);
        const aIsLaptop = isLaptopIntegratedCam(aLabel);
        const bIsLaptop = isLaptopIntegratedCam(bLabel);

        if (aIsLaptop && !bIsLaptop) return -1;
        if (!aIsLaptop && bIsLaptop) return 1;
        if (!aIsPhone && bIsPhone) return -1;
        if (aIsPhone && !bIsPhone) return 1;
        return 0;
      });

      const formatted = sorted.map(d => {
        const raw = d.label || 'Webcam';
        let displayLabel = raw;
        if (isMobileOrLinkedCamera(raw)) {
          displayLabel = `📱 ${raw} (Mobile / Linked)`;
        } else if (isLaptopIntegratedCam(raw)) {
          displayLabel = `💻 Built-in Laptop Webcam (${raw})`;
        } else {
          displayLabel = `📷 ${raw}`;
        }
        return { deviceId: d.deviceId, label: displayLabel };
      });

      setAvailableCameras(formatted);
      return formatted;
    } catch {
      return [];
    }
  };

  // Switch active camera stream directly to a specific device ID
  const switchCamera = async (targetDeviceId: string) => {
    if (!targetDeviceId) return;
    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      setSelectedCameraId(targetDeviceId);
      try {
        localStorage.setItem('markus_preferred_camera', targetDeviceId);
      } catch {}

      let newStream: MediaStream | null = null;
      try {
        newStream = await navigator.mediaDevices.getUserMedia({
          video: {
            deviceId: { exact: targetDeviceId },
            width: { ideal: 640 },
            height: { ideal: 480 },
          },
          audio: false,
        });
      } catch {
        newStream = await navigator.mediaDevices.getUserMedia({
          video: {
            deviceId: { ideal: targetDeviceId },
            width: { ideal: 640 },
            height: { ideal: 480 },
          },
          audio: false,
        });
      }

      if (newStream) {
        streamRef.current = newStream;
        if (videoRef.current) {
          videoRef.current.srcObject = newStream;
          videoRef.current.muted = true;
          await videoRef.current.play().catch(() => {});
        }
      }
    } catch (err: any) {
      console.warn('Switch camera error, falling back:', err);
    }
  };

  const cameraActiveRef = useRef<boolean>(false);

  useEffect(() => {
    cameraActiveRef.current = cameraActive;
    if (!cameraActive) {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (backendTimerRef.current) clearTimeout(backendTimerRef.current);
      return;
    }

    let isSubscribed = true;

    const runClientLoop = async () => {
      if (!isSubscribed || !cameraActiveRef.current) return;
      try {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (video && canvas && video.readyState >= 2 && video.videoWidth > 0 && !video.paused && !video.ended) {
          const ctx = canvas.getContext('2d', { willReadFrequently: true });
          if (ctx) {
            const vw = video.videoWidth;
            const vh = video.videoHeight;
            const aspect = vh > 0 ? vw / vh : 4 / 3;
            const targetW = 320;
            const targetH = Math.max(160, Math.round(320 / aspect));
            if (canvas.width !== targetW || canvas.height !== targetH) {
              canvas.width = targetW;
              canvas.height = targetH;
            }
            ctx.drawImage(video, 0, 0, targetW, targetH);
            await analyzeClientSideFrame(ctx, targetW, targetH);
          }
        }
      } catch (err) {
        console.warn('Client loop frame notice:', err);
      }

      if (isSubscribed && cameraActiveRef.current) {
        timerRef.current = setTimeout(runClientLoop, 100);
      }
    };

    const runBackendLoop = async () => {
      if (!isSubscribed || !cameraActiveRef.current || !backendAvailableRef.current) return;
      await syncBackendFrame();
      if (isSubscribed && cameraActiveRef.current) {
        backendTimerRef.current = setTimeout(runBackendLoop, 250);
      }
    };

    timerRef.current = setTimeout(runClientLoop, 80);
    backendTimerRef.current = setTimeout(runBackendLoop, 200);

    return () => {
      isSubscribed = false;
      if (timerRef.current) clearTimeout(timerRef.current);
      if (backendTimerRef.current) clearTimeout(backendTimerRef.current);
    };
  }, [cameraActive]);

  // Stop Camera
  const stopCamera = async () => {
    cameraActiveRef.current = false;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (backendTimerRef.current) {
      clearTimeout(backendTimerRef.current);
      backendTimerRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    smoothedBoxRef.current = null;
    setCameraActive(false);
    setFaceCount(0);
    setFaces([]);
    setHedgedText('Webcam paused');
    try {
      await fetch('/api/vision/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: false }),
      });
    } catch {}
  };

  // Start Camera
  const startCamera = async () => {
    if (cameraActiveRef.current && streamRef.current?.active) return;
    try {
      setHedgedText('Starting camera...');
      let stream: MediaStream | null = null;

      // 1. Enumerate available video devices
      const initialDevices = await navigator.mediaDevices.enumerateDevices().catch(() => []);
      const videoDevs = initialDevices.filter(d => d.kind === 'videoinput');

      // Check if saved preferred camera still exists
      let savedId = '';
      try {
        savedId = localStorage.getItem('markus_preferred_camera') || '';
      } catch {}

      let targetId = '';
      if (savedId && videoDevs.some(d => d.deviceId === savedId)) {
        targetId = savedId;
      } else if (selectedCameraId && videoDevs.some(d => d.deviceId === selectedCameraId)) {
        targetId = selectedCameraId;
      }

      // Find laptop integrated webcam candidate
      const laptopCam = videoDevs.find(d => isLaptopIntegratedCam(d.label)) ||
        videoDevs.find(d => d.label && !isMobileOrLinkedCamera(d.label));

      if (laptopCam && laptopCam.deviceId) {
        targetId = laptopCam.deviceId;
      }

      // Level 1: Target specific laptop camera by deviceId
      if (targetId) {
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { deviceId: { ideal: targetId }, width: { ideal: 640 }, height: { ideal: 480 } },
            audio: false,
          });
        } catch {}
      }

      // Level 2: Try each non-phone candidate in videoDevs
      if (!stream && videoDevs.length > 0) {
        const nonPhoneList = videoDevs.filter(d => !isMobileOrLinkedCamera(d.label));
        const listToTry = nonPhoneList.length > 0 ? nonPhoneList : videoDevs;

        for (const dev of listToTry) {
          try {
            stream = await navigator.mediaDevices.getUserMedia({
              video: { deviceId: { ideal: dev.deviceId }, width: { ideal: 640 }, height: { ideal: 480 } },
              audio: false,
            });
            if (stream) {
              targetId = dev.deviceId;
              break;
            }
          } catch {}
        }
      }

      // Level 3: Fallback to standard user-facing or general camera
      if (!stream) {
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: { ideal: 'user' }, width: { ideal: 640 }, height: { ideal: 480 } },
            audio: false,
          });
        } catch {
          stream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false,
          });
        }
      }

      if (!stream) throw new Error('No video stream received from camera');

      // Refresh device list now that permissions reveal all labels
      const allDevices = await refreshCameraDevices();
      const activeTrack = stream.getVideoTracks()[0];
      const activeLabel = activeTrack ? (activeTrack.label || '') : '';

      // If the active track is a mobile / phone camera and a built-in laptop camera is available, switch gracefully
      if (isMobileOrLinkedCamera(activeLabel)) {
        const freshLaptopCam = allDevices.find(d => !isMobileOrLinkedCamera(d.label));
        if (freshLaptopCam && freshLaptopCam.deviceId) {
          try {
            const laptopStream = await navigator.mediaDevices.getUserMedia({
              video: { deviceId: { ideal: freshLaptopCam.deviceId }, width: { ideal: 640 }, height: { ideal: 480 } },
              audio: false,
            });
            if (laptopStream) {
              stream.getTracks().forEach(t => t.stop());
              stream = laptopStream;
              targetId = freshLaptopCam.deviceId;
              setSelectedCameraId(freshLaptopCam.deviceId);
              try {
                localStorage.setItem('markus_preferred_camera', freshLaptopCam.deviceId);
              } catch {}
            }
          } catch {}
        }
      } else if (targetId) {
        setSelectedCameraId(targetId);
        try {
          localStorage.setItem('markus_preferred_camera', targetId);
        } catch {}
      }

      const freshTrack = stream.getVideoTracks()[0];
      if (freshTrack) {
        freshTrack.onended = () => {
          if (cameraActiveRef.current) {
            setTimeout(() => {
              if (cameraActiveRef.current) startCamera();
            }, 1000);
          }
        };
      }

      streamRef.current = stream;
      cameraActiveRef.current = true;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.muted = true;
        try {
          await videoRef.current.play();
        } catch {
          videoRef.current.play().catch(() => {});
        }
      }

      setCameraActive(true);
      setFaceCount(0);
      setHedgedText('Camera active — tracking faces and expressions...');

      try {
        await fetch('/api/vision/toggle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: true, emotion_enabled: emotionActive }),
        });
      } catch {}
    } catch (err: any) {
      console.error('Could not access camera:', err);
      let msg = 'Access denied or device busy';
      if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError') {
        msg = 'Camera permission blocked. Check browser address bar or Windows Settings > Privacy > Camera.';
      } else if (err?.name === 'NotFoundError' || err?.name === 'DevicesNotFoundError') {
        msg = 'Camera not found. Check Device Manager or ensure camera privacy shutter is open.';
      } else if (err?.name === 'NotReadableError' || err?.name === 'TrackStartError') {
        msg = 'Camera is in use by another app (Teams, Zoom, Camera app). Close other apps and retry.';
      } else if (err?.message) {
        msg = err.message;
      }
      setHedgedText(`Camera notice: ${msg}`);
      cameraActiveRef.current = false;
      setCameraActive(false);
    }
  };

  // Toggle Camera
  const toggleCamera = async () => {
    if (cameraActive) {
      await stopCamera();
    } else {
      await startCamera();
    }
  };

  const syncBackendFrame = async () => {
    if (!videoRef.current || !canvasRef.current || !cameraActiveRef.current || !backendAvailableRef.current) return;
    const canvas = canvasRef.current;
    if (canvas.width === 0) return;

    try {
      const base64Image = canvas.toDataURL('image/jpeg', 0.55);
      const res = await fetch('/api/vision/analyze-frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: base64Image }),
      }).catch(() => null);

      if (res && res.ok) {
        backendAvailableRef.current = true;
        const data = await res.json();
        if (data.hedged_description) {
          setHedgedText(data.hedged_description);
        }
        if (data.face_count !== undefined && data.face_count > 0) {
          consecutiveMissesRef.current = 0;
          lastBackendSuccessRef.current = Date.now();
          setFaceCount(data.face_count);
          if (data.expression) setExpression(data.expression);
          if (data.expression_confidence) setConfidence(data.expression_confidence);

          if (data.faces && data.faces.length > 0) {
            const vWidth = videoRef.current?.videoWidth || 640;
            const vHeight = videoRef.current?.videoHeight || 480;
            const cRect = containerRef.current?.getBoundingClientRect();
            const cWidth = cRect?.width || 320;
            const cHeight = cRect?.height || 190;

            const parsedFaces: TrackedFaceItem[] = data.faces.map((f: any, idx: number) => {
              const norm = f.normalized_bbox || {};
              const nx = typeof norm.x === 'number' ? norm.x : 0.2;
              const ny = typeof norm.y === 'number' ? norm.y : 0.15;
              const nw = typeof norm.w === 'number' ? norm.w : 0.45;
              const nh = typeof norm.h === 'number' ? norm.h : 0.55;

              const coverBox = computeVideoCoverRect(nx, ny, nw, nh, vWidth, vHeight, cWidth, cHeight, true);

              const isKnown = f.identity && f.identity !== 'Unknown';
              const identityName = isKnown ? f.identity : 'Unknown';
              const displayLabel = isKnown ? f.identity : (idx === 0 ? 'Unknown' : `Unknown (#${idx + 1})`);
              return {
                trackId: f.track_id || (idx + 1),
                identity: identityName,
                label: displayLabel,
                expression: f.expression || data.expression || 'neutral',
                confidence: f.expression_confidence || data.expression_confidence || 0.85,
                box: coverBox,
              };
            });
            setFaces(parsedFaces);
          }
        } else if (data.face_count === 0) {
          consecutiveMissesRef.current += 1;
          if (consecutiveMissesRef.current > 15) {
            setFaceCount(0);
            setFaces([]);
          }
        }
      }
    } catch {
      // Backend sync silent fallback
    }
  };

  const syncKnownFacesFromBackend = async () => {
    try {
      const res = await fetch('/api/vision/known-faces');
      if (res.ok) {
        const data = await res.json();
        if (data.known_faces && Array.isArray(data.known_faces) && data.known_faces.length > 0) {
          setRegisteredFaces(data.known_faces);
          try {
            localStorage.setItem('markus_known_faces', JSON.stringify(data.known_faces));
          } catch {}
        }
      }
    } catch {}
  };

  const handleDeleteFace = async (nameToDelete: string) => {
    const updated = registeredFaces.filter(n => n !== nameToDelete);
    const finalFaces = updated.length > 0 ? updated : ['Kavihai Arasu (Owner)'];
    setRegisteredFaces(finalFaces);
    const updatedProfiles = faceProfiles.filter(p => p.name !== nameToDelete);
    setFaceProfiles(updatedProfiles);
    try {
      localStorage.setItem('markus_known_faces', JSON.stringify(finalFaces));
      localStorage.setItem('markus_known_face_profiles', JSON.stringify(updatedProfiles));
    } catch {}

    try {
      await fetch(`/api/vision/known-faces/${encodeURIComponent(nameToDelete)}`, {
        method: 'DELETE',
      });
    } catch {}
  };

  useEffect(() => {
    refreshCameraDevices();
    syncKnownFacesFromBackend();

    // Always-on camera: Automatically start camera on mount
    const startTimer = setTimeout(() => {
      if (!cameraActiveRef.current) {
        startCamera();
      }
    }, 150);

    const handleDeviceChange = () => {
      refreshCameraDevices();
    };

    const handleVisibility = () => {
      if (document.visibilityState === 'visible' && !cameraActiveRef.current) {
        startCamera();
      }
    };

    if (navigator.mediaDevices?.addEventListener) {
      navigator.mediaDevices.addEventListener('devicechange', handleDeviceChange);
    }
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      clearTimeout(startTimer);
      if (navigator.mediaDevices?.removeEventListener) {
        navigator.mediaDevices.removeEventListener('devicechange', handleDeviceChange);
      }
      document.removeEventListener('visibilitychange', handleVisibility);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (timerRef.current) clearTimeout(timerRef.current);
      if (backendTimerRef.current) clearTimeout(backendTimerRef.current);
    };
  }, []);

  const handleRegisterCurrentFace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!registerName.trim()) return;

    const trimmedName = registerName.trim();
    const updated = [trimmedName, ...registeredFaces.filter(n => n !== trimmedName)];
    setRegisteredFaces(updated);
    try {
      localStorage.setItem('markus_known_faces', JSON.stringify(updated));
    } catch {}

    if (canvasRef.current && cameraActive) {
      try {
        const ctx = canvasRef.current.getContext('2d');
        if (ctx) {
          const cw = canvasRef.current.width;
          const ch = canvasRef.current.height;
          let fx = 0, fy = 0, fw = cw, fh = ch;
          if (lastDetectedNormBoxRef.current) {
            const nb = lastDetectedNormBoxRef.current;
            fx = Math.max(0, Math.floor(nb.x * cw));
            fy = Math.max(0, Math.floor(nb.y * ch));
            fw = Math.min(cw - fx, Math.floor(nb.w * cw));
            fh = Math.min(ch - fy, Math.floor(nb.h * ch));
          } else {
            fx = Math.floor(cw * 0.25);
            fy = Math.floor(ch * 0.15);
            fw = Math.floor(cw * 0.50);
            fh = Math.floor(ch * 0.70);
          }
          const imgData = ctx.getImageData(0, 0, cw, ch);
          const sig = extractClientFaceSignature(imgData.data, cw, ch, fx, fy, fw, fh);
          if (sig) {
            const newProfiles = [{ name: trimmedName, embedding: sig }, ...faceProfiles.filter(p => p.name !== trimmedName)];
            setFaceProfiles(newProfiles);
            try {
              localStorage.setItem('markus_known_face_profiles', JSON.stringify(newProfiles));
            } catch {}
          }
        }
        const base64 = canvasRef.current.toDataURL('image/jpeg', 0.85);
        await fetch('/api/vision/register-face', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: trimmedName, image_base64: base64 }),
        });
        await syncKnownFacesFromBackend();
      } catch {}
    }

    setRegisterSuccessMsg(`Face profile saved for '${trimmedName}'!`);
    setTimeout(() => {
      setRegisterSuccessMsg('');
      setShowRegisterModal(false);
    }, 1200);
  };

  const currentMeta = EMOTION_META[expression] || EMOTION_META.neutral;

  return (
    <div style={{
      background: 'rgba(7, 11, 20, 0.85)',
      border: '1px solid rgba(0, 229, 255, 0.2)',
      borderRadius: 20,
      padding: 16,
      backdropFilter: 'blur(25px)',
      boxShadow: '0 12px 40px rgba(0, 0, 0, 0.5), inset 0 0 20px rgba(0, 229, 255, 0.05)',
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
      width: '100%',
      minHeight: 440,
      position: 'relative',
      overflow: 'hidden',
      contain: 'paint',
    }}>
      {/* HUD Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: cameraActive ? '#00E5FF' : '#EF4444',
            boxShadow: cameraActive ? '0 0 10px #00E5FF' : '0 0 6px #EF4444',
          }} />
          <span style={{
            fontSize: '0.82rem',
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-heading)',
          }}>
            Face Recognition & Emotion HUD
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {cameraActive && (
            <button
              onClick={() => setShowRegisterModal(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                padding: '5px 10px',
                borderRadius: 8,
                fontSize: '0.70rem',
                fontWeight: 600,
                cursor: 'pointer',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                background: 'rgba(16, 185, 129, 0.12)',
                color: '#10B981',
                transition: 'all 0.2s ease',
              }}
            >
              <UserPlus size={12} />
              REMEMBER FACE
            </button>
          )}

          <button
            onClick={toggleCamera}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '5px 12px',
              borderRadius: 8,
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer',
              border: cameraActive ? '1px solid #00E5FF' : '1px solid rgba(255,255,255,0.12)',
              background: cameraActive ? 'rgba(0, 229, 255, 0.15)' : 'rgba(255,255,255,0.04)',
              color: cameraActive ? '#00E5FF' : 'var(--text-muted)',
              transition: 'all 0.2s ease',
            }}
          >
            {cameraActive ? <Camera size={13} /> : <CameraOff size={13} />}
            {cameraActive ? 'CAM ACTIVE' : 'ENABLE CAM'}
          </button>
        </div>
      </div>

      {/* Face Registration Modal */}
      {showRegisterModal && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(5, 7, 13, 0.92)',
          backdropFilter: 'blur(10px)',
          zIndex: 50,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 20,
        }}>
          <div style={{
            background: '#0B1120',
            border: '1px solid rgba(0, 229, 255, 0.3)',
            borderRadius: 16,
            padding: 20,
            width: '100%',
            maxWidth: 320,
            boxShadow: '0 12px 30px rgba(0,0,0,0.8)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#00E5FF', display: 'flex', alignItems: 'center', gap: 6 }}>
                <UserPlus size={15} />
                Register Face Identity
              </div>
              <button
                onClick={() => setShowRegisterModal(false)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleRegisterCurrentFace} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Look at the camera. Enter your name or identity tag to recognize your face in real time:
              </div>

              <input
                type="text"
                value={registerName}
                onChange={e => setRegisterName(e.target.value)}
                placeholder="e.g. Kavihai Arasu (Owner)"
                style={{
                  width: '100%',
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(0, 229, 255, 0.25)',
                  borderRadius: 8,
                  padding: '8px 12px',
                  color: '#FFFFFF',
                  fontSize: '0.80rem',
                  outline: 'none',
                }}
              />

              {registerSuccessMsg && (
                <div style={{ fontSize: '0.72rem', color: '#10B981', display: 'flex', alignItems: 'center', gap: 5 }}>
                  <Check size={12} />
                  {registerSuccessMsg}
                </div>
              )}

              <button
                type="submit"
                style={{
                  width: '100%',
                  background: 'linear-gradient(135deg, #00E5FF 0%, #0077FF 100%)',
                  border: 'none',
                  borderRadius: 8,
                  padding: '8px 14px',
                  color: '#04070F',
                  fontWeight: 700,
                  fontSize: '0.78rem',
                  cursor: 'pointer',
                }}
              >
                Save Face Profile
              </button>
            </form>

            {registeredFaces && registeredFaces.length > 0 && (
              <div style={{ marginTop: 16, borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 12 }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Registered Profiles ({registeredFaces.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 120, overflowY: 'auto' }}>
                  {registeredFaces.map((name) => (
                    <div
                      key={name}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '5px 8px',
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(255,255,255,0.06)',
                        borderRadius: 6,
                        fontSize: '0.72rem',
                      }}
                    >
                      <span style={{ color: '#00E5FF', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {name}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleDeleteFace(name)}
                        title={`Remove profile ${name}`}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#EF4444',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          padding: 2,
                          opacity: 0.8,
                          transition: 'opacity 0.2s ease',
                        }}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Futuristic Video Stream Container with HUD overlays */}
      <div
        ref={containerRef}
        style={{
          position: 'relative',
          width: '100%',
          height: 190,
          borderRadius: 14,
          overflow: 'hidden',
          background: '#04070F',
          border: '1px solid rgba(0, 229, 255, 0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        {/* HUD Corner Brackets */}
        <div style={{ position: 'absolute', top: 6, left: 6, width: 10, height: 10, borderTop: '2px solid #00E5FF', borderLeft: '2px solid #00E5FF', pointerEvents: 'none', zIndex: 5 }} />
        <div style={{ position: 'absolute', top: 6, right: 6, width: 10, height: 10, borderTop: '2px solid #00E5FF', borderRight: '2px solid #00E5FF', pointerEvents: 'none', zIndex: 5 }} />
        <div style={{ position: 'absolute', bottom: 6, left: 6, width: 10, height: 10, borderBottom: '2px solid #00E5FF', borderLeft: '2px solid #00E5FF', pointerEvents: 'none', zIndex: 5 }} />
        <div style={{ position: 'absolute', bottom: 6, right: 6, width: 10, height: 10, borderBottom: '2px solid #00E5FF', borderRight: '2px solid #00E5FF', pointerEvents: 'none', zIndex: 5 }} />

        {/* Video feed */}
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            display: cameraActive ? 'block' : 'none',
            transform: 'scaleX(-1)',
          }}
        />
        <canvas ref={canvasRef} style={{ display: 'none' }} />

        {/* Real-Time Multi-Face Bounding Box & Emotion Tag Overlay */}
        {cameraActive && faces.map((f, idx) => {
          const rawName = f.identity || f.label || '';
          const isUnknown = !rawName || rawName.toLowerCase().includes('unknown');
          const displayName = isUnknown ? (faces.length > 1 && idx > 0 ? `UNKNOWN #${idx + 1}` : 'UNKNOWN') : rawName;
          const boxBorderColor = isUnknown ? '#F59E0B' : '#00E5FF';
          const boxGlow = isUnknown
            ? '0 0 16px rgba(245, 158, 11, 0.45), inset 0 0 8px rgba(245, 158, 11, 0.15)'
            : '0 0 16px rgba(0, 229, 255, 0.45), inset 0 0 8px rgba(0, 229, 255, 0.15)';
          const badgeGradient = isUnknown
            ? 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)'
            : 'linear-gradient(135deg, #00E5FF 0%, #0077FF 100%)';

          return (
            <div
              key={f.trackId}
              style={{
                position: 'absolute',
                left: `${f.box.x}%`,
                top: `${f.box.y}%`,
                width: `${f.box.width}%`,
                height: `${f.box.height}%`,
                border: `2px solid ${boxBorderColor}`,
                borderRadius: 6,
                pointerEvents: 'none',
                boxShadow: boxGlow,
                transition: 'all 0.08s ease-out',
                zIndex: 6,
              }}
            >
              <div style={{
                position: 'absolute',
                top: -24,
                left: -2,
                background: badgeGradient,
                borderRadius: '4px 4px 0 0',
                padding: '2px 8px',
                fontSize: '0.70rem',
                fontWeight: 800,
                color: '#04070F',
                fontFamily: 'var(--font-code), monospace',
                whiteSpace: 'nowrap',
                letterSpacing: '0.03em',
                boxShadow: '0 2px 8px rgba(0,0,0,0.6)',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}>
                <span>👤 {displayName.toUpperCase()}</span>
                <span>• {f.expression.toUpperCase()}</span>
              </div>
            </div>
          );
        })}

        {/* HUD scanlines */}
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%)',
          backgroundSize: '100% 2px',
          pointerEvents: 'none',
          zIndex: 3,
        }} />

        {!cameraActive && (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 16, zIndex: 4 }}>
            <CameraOff size={28} style={{ margin: '0 auto 6px', opacity: 0.5, color: '#00E5FF' }} />
            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}>Vision Stream Paused</div>
            <div style={{ fontSize: '0.68rem', opacity: 0.7, marginTop: 3 }}>Click "ENABLE CAM" to start face & emotion tracking</div>
          </div>
        )}

        {cameraActive && (
          <div style={{
            position: 'absolute',
            bottom: 8,
            left: 8,
            background: 'rgba(5, 7, 13, 0.85)',
            border: '1px solid rgba(0, 229, 255, 0.25)',
            borderRadius: 6,
            padding: '3px 8px',
            fontSize: '0.65rem',
            color: '#00E5FF',
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            backdropFilter: 'blur(6px)',
            zIndex: 6,
          }}>
            <UserCheck size={11} />
            <span>FACES DETECTED: {faceCount}</span>
          </div>
        )}
      </div>

      {/* Emotion Telemetry Card (Fixed Layout & Stable Heights) */}
      <div style={{
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid rgba(255, 255, 255, 0.06)',
        borderRadius: 12,
        padding: '12px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        minHeight: 145,
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 40 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '1.4rem' }}>{currentMeta.emoji}</span>
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: currentMeta.color, transition: 'color 0.2s ease' }}>
                {faceCount > 0 
                  ? `${faces[0]?.identity && !faces[0]?.identity.toLowerCase().includes('unknown') ? faces[0].identity : 'Unknown'} — ${currentMeta.label}` 
                  : 'No Face In View'}
              </div>
              <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>
                {faceCount > 0 
                  ? (faces[0]?.identity && !faces[0]?.identity.toLowerCase().includes('unknown') 
                      ? '✓ Verified Facial Biometric Profile' 
                      : '⚠️ Unregistered / Unknown Face Biometrics') 
                  : 'Awaiting subject presence'}
              </div>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, fontFamily: 'var(--font-code)', color: currentMeta.color, transition: 'color 0.2s ease' }}>
              {faceCount > 0 ? `${Math.round(confidence * 100)}%` : '0%'}
            </div>
            <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>Confidence</div>
          </div>
        </div>

        {/* Hedged perception context string */}
        <div style={{
          fontSize: '0.70rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.35,
          fontStyle: 'italic',
          background: 'rgba(0, 0, 0, 0.25)',
          padding: '6px 8px',
          borderRadius: 6,
          borderLeft: `2px solid ${currentMeta.color}`,
          minHeight: 36,
          display: 'flex',
          alignItems: 'center',
          transition: 'border-color 0.2s ease',
        }}>
          "{hedgedText}"
        </div>

        {/* Real-time 7-Emotion Live Probability Meters */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
          padding: '6px 8px',
          borderRadius: 8,
          background: 'rgba(0, 0, 0, 0.3)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
        }}>
          <div style={{ fontSize: '0.62rem', fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            Real-Time Emotion Probabilities
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 4 }}>
            {Object.entries(EMOTION_META).slice(0, 4).map(([emoKey, emoMeta]) => {
              const score = emotionScores[emoKey] ?? (emoKey === expression ? confidence : 0.02);
              const pct = Math.round(score * 100);
              const isSelected = expression === emoKey;
              return (
                <div key={emoKey} style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 2,
                  padding: '3px 4px',
                  borderRadius: 4,
                  background: isSelected ? 'rgba(255, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                  border: isSelected ? `1px solid ${emoMeta.color}60` : '1px solid transparent',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.58rem', color: isSelected ? emoMeta.color : 'var(--text-muted)' }}>
                    <span>{emoMeta.emoji} {emoKey.slice(0, 4)}</span>
                    <span style={{ fontFamily: 'var(--font-code)' }}>{pct}%</span>
                  </div>
                  <div style={{ width: '100%', height: 3, background: 'rgba(255,255,255,0.08)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{ width: `${pct}%`, height: '100%', background: emoMeta.color, transition: 'width 0.2s ease' }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Screen & Routing Perception Status */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 6,
          fontSize: '0.65rem',
          fontFamily: 'var(--font-code)',
        }}>
          <div style={{
            background: 'rgba(0, 229, 255, 0.05)',
            border: '1px solid rgba(0, 229, 255, 0.15)',
            borderRadius: 6,
            padding: '4px 6px',
            color: '#00E5FF',
            textAlign: 'center',
          }}>
            MULTI-FACE: {faceCount > 0 ? 'TRACKING' : 'SCANNING'}
          </div>
          <div style={{
            background: 'rgba(16, 185, 129, 0.05)',
            border: '1px solid rgba(16, 185, 129, 0.15)',
            borderRadius: 6,
            padding: '4px 6px',
            color: '#10B981',
            textAlign: 'center',
          }}>
            EMOTION: {expression.toUpperCase()} ({Math.round(confidence * 100)}%)
          </div>
        </div>
      </div>
    </div>
  );
}


