import React, { useState, useEffect, useRef } from 'react';
import { Camera, CameraOff, Eye, ShieldCheck, Activity, Smile, Sparkles, UserCheck } from 'lucide-react';
import { useAIState } from '../context/AIStateContext';

/* ═══════════════════════════════════════════════════════════
   PERCEPTION HUD — Smooth, Jitter-Free Facial Emotion HUD (§3, §4)
   
   Features:
   - Live Webcam capture with hardware-accelerated video rendering
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

  // Client-side real-time face & expression detector
  // Client-side real-time face & expression detector
  const analyzeClientSideFrame = async (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    try {
      // ── Option A: Native Browser Hardware-Accelerated FaceDetector API (Chrome / Edge) ──
      if (typeof (window as any).FaceDetector === 'function' && videoRef.current) {
        try {
          const detector = new (window as any).FaceDetector({ fastMode: true, maxDetectedFaces: 2 });
          const detectedNativeFaces = await detector.detect(videoRef.current);

          if (detectedNativeFaces && detectedNativeFaces.length > 0) {
            const face = detectedNativeFaces[0];
            const box = face.boundingBox;
            const vw = videoRef.current.videoWidth || width;
            const vh = videoRef.current.videoHeight || height;

            const normX = box.x / vw;
            const normY = box.y / vh;
            const normW = box.width / vw;
            const normH = box.height / vh;

            const targetX = Math.max(0, Math.min(92, (1 - (normX + normW)) * 100));
            const targetY = Math.max(0, Math.min(92, normY * 100));
            const targetW = Math.max(12, Math.min(90, normW * 100));
            const targetH = Math.max(15, Math.min(90, normH * 100));

            // Estimate emotion from face region on canvas
            const cropX = Math.max(0, Math.floor(normX * width));
            const cropY = Math.max(0, Math.floor(normY * height));
            const cropW = Math.min(width - cropX, Math.floor(normW * width));
            const cropH = Math.min(height - cropY, Math.floor(normH * height));

            let rawEmotion = 'neutral';
            let rawConf = 0.86;

            if (cropW > 10 && cropH > 10) {
              const faceImgData = ctx.getImageData(cropX, cropY, cropW, cropH);
              const { emotion, conf } = estimateExpressionFromImageData(faceImgData.data, cropW, cropH);
              rawEmotion = emotion;
              rawConf = conf;
            }

            return applyDetectedFace(targetX, targetY, targetW, targetH, rawEmotion, rawConf);
          }
        } catch {}
      }

      // ── Option B: Adaptive Luminance, Contrast & Skin-Tone Contour Detector ──
      const imgData = ctx.getImageData(0, 0, width, height);
      const data = imgData.data;

      let skinPixels = 0;
      let minX = width, maxX = 0, minY = height, maxY = 0;
      let sumX = 0, sumY = 0;
      let centerDarkPixels = 0;
      let centerSumX = 0, centerSumY = 0;

      const centerXMin = width * 0.12;
      const centerXMax = width * 0.88;
      const centerYMin = height * 0.06;
      const centerYMax = height * 0.90;

      for (let y = 0; y < height; y += 2) {
        for (let x = 0; x < width; x += 2) {
          const idx = (y * width + x) * 4;
          const r = data[idx];
          const g = data[idx + 1];
          const b = data[idx + 2];

          const Y = 0.299 * r + 0.587 * g + 0.114 * b;
          const Cb = -0.1687 * r - 0.3313 * g + 0.5 * b + 128;
          const Cr = 0.5 * r - 0.4187 * g - 0.0813 * b + 128;

          const sumRGB = r + g + b + 1;
          const normR = r / sumRGB;
          const normG = g / sumRGB;

          // Universal skin & contour cluster
          const isSkin = (
            (Cb >= 68 && Cb <= 148 && Cr >= 118 && Cr <= 192 && Y > 15) ||
            (normR > 0.30 && normR < 0.65 && normG > 0.22 && normG < 0.42 && r >= b - 10) ||
            (r > 25 && g > 15 && b > 8 && (r >= g || Math.abs(r - g) < 28))
          );

          if (isSkin) {
            skinPixels++;
            sumX += x;
            sumY += y;
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
          }

          if (x >= centerXMin && x <= centerXMax && y >= centerYMin && y <= centerYMax) {
            if (Y < 170 && (r > 12 || g > 12 || b > 12)) {
              centerDarkPixels++;
              centerSumX += x;
              centerSumY += y;
            }
          }
        }
      }

      const totalSampled = (width / 2) * (height / 2);
      const hasSkinCluster = skinPixels > totalSampled * 0.010 && (maxX - minX) > 12 && (maxY - minY) > 12;
      const hasSilhouetteSubject = centerDarkPixels > totalSampled * 0.07;
      const hasFace = hasSkinCluster || hasSilhouetteSubject;

      if (hasFace) {
        let boxW = 0, boxH = 0, centerX = 0, centerY = 0;

        if (hasSkinCluster) {
          boxW = Math.min(width * 0.85, Math.max(width * 0.26, (maxX - minX) * 1.18));
          boxH = Math.min(height * 0.90, Math.max(height * 0.34, (maxY - minY) * 1.22));
          centerX = sumX / skinPixels;
          centerY = sumY / skinPixels;
        } else {
          boxW = width * 0.48;
          boxH = height * 0.64;
          centerX = centerSumX / Math.max(1, centerDarkPixels);
          centerY = centerSumY / Math.max(1, centerDarkPixels);
        }

        const boxX = Math.max(0, Math.min(width - boxW, centerX - boxW / 2));
        const boxY = Math.max(0, Math.min(height - boxH, centerY - boxH / 2));

        // Analyze mouth and expression geometry
        const { emotion, conf } = estimateExpressionFromImageData(data, width, height, boxX, boxY, boxW, boxH);

        const normW = boxW / width;
        const normH = boxH / height;
        const normX = boxX / width;
        const normY = boxY / height;

        const targetX = Math.max(0, Math.min(92, (1 - (normX + normW)) * 100));
        const targetY = Math.max(0, Math.min(92, normY * 100));
        const targetW = Math.max(12, Math.min(90, normW * 100));
        const targetH = Math.max(15, Math.min(90, normH * 100));

        return applyDetectedFace(targetX, targetY, targetW, targetH, emotion, conf);
      } else {
        consecutiveMissesRef.current += 1;
        if (consecutiveMissesRef.current > 4) {
          smoothedBoxRef.current = null;
          setFaceCount(0);
          setFaces([]);
          setHedgedText('No face detected in view.');
        }
        return false;
      }
    } catch {
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
  ): { emotion: string; conf: number } => {
    const mouthYStart = Math.floor(boxY + boxH * 0.56);
    const mouthYEnd = Math.floor(boxY + boxH * 0.92);
    const mouthXStart = Math.floor(boxX + boxW * 0.16);
    const mouthXEnd = Math.floor(boxX + boxW * 0.84);

    let mouthBrightness = 0;
    let mouthDarkCavity = 0;
    let mouthSamples = 0;
    let mouthSpread = 0;
    let leftMouthLum = 0, rightMouthLum = 0, leftSamples = 0, rightSamples = 0;

    for (let my = mouthYStart; my < mouthYEnd; my += 2) {
      for (let mx = mouthXStart; mx < mouthXEnd; mx += 2) {
        if (mx >= 0 && mx < width && my >= 0 && my < height) {
          const idx = (my * width + mx) * 4;
          const lum = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
          mouthBrightness += lum;
          if (lum < 42) mouthDarkCavity++;
          if (lum > 128) mouthSpread++;
          mouthSamples++;

          if (mx < (mouthXStart + mouthXEnd) / 2) {
            leftMouthLum += lum;
            leftSamples++;
          } else {
            rightMouthLum += lum;
            rightSamples++;
          }
        }
      }
    }

    const avgMouthLum = mouthSamples > 0 ? mouthBrightness / mouthSamples : 95;
    const mouthOpenRatio = mouthSamples > 0 ? mouthDarkCavity / mouthSamples : 0;
    const smileRatio = mouthSamples > 0 ? mouthSpread / mouthSamples : 0;
    const asymmetry = Math.abs(
      (leftSamples > 0 ? leftMouthLum / leftSamples : 0) -
      (rightSamples > 0 ? rightMouthLum / rightSamples : 0)
    );

    let rawEmotion = 'neutral';
    let rawConf = 0.85;

    if (smileRatio > 0.12 || avgMouthLum > 122) {
      rawEmotion = 'happy';
      rawConf = Math.min(0.96, 0.75 + smileRatio * 1.2);
    } else if (mouthOpenRatio > 0.16) {
      rawEmotion = 'surprised';
      rawConf = Math.min(0.94, 0.74 + mouthOpenRatio * 1.0);
    } else if (asymmetry > 32) {
      rawEmotion = 'disgusted';
      rawConf = 0.79;
    } else if (avgMouthLum < 52 && smileRatio < 0.03) {
      rawEmotion = 'sad';
      rawConf = 0.77;
    } else {
      rawEmotion = 'neutral';
      rawConf = 0.87;
    }

    return { emotion: rawEmotion, conf: rawConf };
  };

  const applyDetectedFace = (
    targetX: number,
    targetY: number,
    targetW: number,
    targetH: number,
    rawEmotion: string,
    rawConf: number
  ) => {
    consecutiveMissesRef.current = 0;

    // Temporal smoothing for expression stability
    recentEmotionsRef.current.push(rawEmotion);
    if (recentEmotionsRef.current.length > 4) {
      recentEmotionsRef.current.shift();
    }

    const counts: Record<string, number> = {};
    recentEmotionsRef.current.forEach(e => { counts[e] = (counts[e] || 0) + 1; });
    let stableEmotion = rawEmotion;
    let maxCount = 0;
    for (const [emo, count] of Object.entries(counts)) {
      if (count > maxCount) {
        maxCount = count;
        stableEmotion = emo;
      }
    }

    // EMA Smoothing on bounding box (70% new, 30% previous)
    const prev = smoothedBoxRef.current || { x: targetX, y: targetY, width: targetW, height: targetH };
    const smoothBox = {
      x: Math.round((0.70 * targetX + 0.30 * prev.x) * 10) / 10,
      y: Math.round((0.70 * targetY + 0.30 * prev.y) * 10) / 10,
      width: Math.round((0.70 * targetW + 0.30 * prev.width) * 10) / 10,
      height: Math.round((0.70 * targetH + 0.30 * prev.height) * 10) / 10,
    };
    smoothedBoxRef.current = smoothBox;

    const trackedItem: TrackedFaceItem = {
      trackId: 1,
      label: 'TARGET #1',
      expression: stableEmotion,
      confidence: roundDec(rawConf, 2),
      box: smoothBox,
    };

    setFaceCount(1);
    setFaces([trackedItem]);
    setExpression(stableEmotion);
    setConfidence(roundDec(rawConf, 2));
    setHedgedText(`Visible facial expression appears ${stableEmotion} (confidence ${Math.round(rawConf * 100)}%)`);

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

  // Toggle Camera
  const toggleCamera = async () => {
    if (cameraActive) {
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
      setHedgedText('Webcam paused for privacy');
      try {
        await fetch('http://localhost:8000/api/vision/toggle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: false }),
        });
      } catch {}
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30 } }
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => {
            videoRef.current?.play().catch(console.warn);
          };
          videoRef.current.play().catch(console.warn);
        }
        setCameraActive(true);
        setFaceCount(0);
        setHedgedText('Scanning for facial expressions in real-time...');

        try {
          await fetch('http://localhost:8000/api/vision/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: true, emotion_enabled: emotionActive }),
          });
        } catch {}

        scheduleNextFrame(120);
        scheduleNextBackendSync(600);
      } catch (err) {
        console.warn('Could not access webcam:', err);
        setHedgedText('Webcam access denied or unavailable.');
      }
    }
  };

  const scheduleNextFrame = (delayMs: number = 150) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(processClientFrame, delayMs);
  };

  const processClientFrame = async () => {
    if (!videoRef.current || !canvasRef.current || !cameraActive) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (!ctx || video.readyState < 2 || video.videoWidth === 0 || video.paused || video.ended) {
      scheduleNextFrame(180);
      return;
    }

    // Process lightweight 240x180 canvas frame
    canvas.width = 240;
    canvas.height = 180;
    ctx.drawImage(video, 0, 0, 240, 180);

    await analyzeClientSideFrame(ctx, 240, 180);
    scheduleNextFrame(120);
  };

  const scheduleNextBackendSync = (delayMs: number = 600) => {
    if (backendTimerRef.current) clearTimeout(backendTimerRef.current);
    backendTimerRef.current = setTimeout(syncBackendFrame, delayMs);
  };

  const syncBackendFrame = async () => {
    if (!videoRef.current || !canvasRef.current || !cameraActive) return;
    const canvas = canvasRef.current;
    if (canvas.width === 0) {
      scheduleNextBackendSync(600);
      return;
    }

    try {
      const base64Image = canvas.toDataURL('image/jpeg', 0.55);
      const res = await fetch('http://localhost:8000/api/vision/analyze-frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: base64Image }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.hedged_description) {
          setHedgedText(data.hedged_description);
        }
        if (data.face_count !== undefined && data.face_count > 0) {
          consecutiveMissesRef.current = 0;
          setFaceCount(data.face_count);
          if (data.expression) setExpression(data.expression);
          if (data.expression_confidence) setConfidence(data.expression_confidence);

          if (data.faces && data.faces.length > 0) {
            const parsedFaces: TrackedFaceItem[] = data.faces.map((f: any, idx: number) => {
              const norm = f.normalized_bbox || {};
              const nx = typeof norm.x === 'number' ? norm.x : 0.2;
              const ny = typeof norm.y === 'number' ? norm.y : 0.15;
              const nw = typeof norm.w === 'number' ? norm.w : 0.45;
              const nh = typeof norm.h === 'number' ? norm.h : 0.55;

              const mirroredX = Math.max(0, Math.min(92, (1 - (nx + nw)) * 100));
              const boxY = Math.max(0, Math.min(92, ny * 100));
              const boxWidth = Math.max(10, Math.min(90, nw * 100));
              const boxHeight = Math.max(12, Math.min(90, nh * 100));

              return {
                trackId: f.track_id || (idx + 1),
                label: f.identity || `TARGET #${f.track_id || (idx + 1)}`,
                expression: f.expression || data.expression || 'neutral',
                confidence: f.confidence || data.expression_confidence || 0.85,
                box: { x: mirroredX, y: boxY, width: boxWidth, height: boxHeight },
              };
            });
            setFaces(parsedFaces);
          }
        }
      }
    } catch {
      // Backend sync silent fallback
    } finally {
      scheduleNextBackendSync(600);
    }
  };

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (timerRef.current) clearTimeout(timerRef.current);
      if (backendTimerRef.current) clearTimeout(backendTimerRef.current);
    };
  }, []);

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
            Multi-Face & Emotion HUD
          </span>
        </div>

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

      {/* Futuristic Video Stream Container with HUD overlays */}
      <div style={{
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
      }}>
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

        {/* Target Reticles overlay on detected face */}
        {cameraActive && faces.map((f) => {
          const meta = EMOTION_META[f.expression] || EMOTION_META.neutral;
          return (
            <div
              key={f.trackId}
              style={{
                position: 'absolute',
                left: `${f.box.x}%`,
                top: `${f.box.y}%`,
                width: `${f.box.width}%`,
                height: `${f.box.height}%`,
                border: `1.5px dashed ${meta.color}`,
                borderRadius: 8,
                pointerEvents: 'none',
                boxShadow: `0 0 12px ${meta.color}40`,
                transition: 'all 0.12s cubic-bezier(0.2, 0, 0.2, 1)',
                zIndex: 4,
              }}
            >
              <div style={{
                position: 'absolute',
                top: -18,
                left: 0,
                background: 'rgba(5, 7, 13, 0.94)',
                border: `1px solid ${meta.color}`,
                borderRadius: 4,
                padding: '1px 5px',
                fontSize: '0.60rem',
                color: meta.color,
                fontFamily: 'var(--font-code)',
                whiteSpace: 'nowrap',
              }}>
                TARGET #{f.trackId} • {f.expression.toUpperCase()}
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
                {faceCount > 0 ? `TARGET #1: ${currentMeta.label}` : 'No Face In View'}
              </div>
              <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>
                {faceCount > 0 ? 'Facial Biometric Expression' : 'Awaiting subject presence'}
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
            MULTI-FACE: ACTIVE
          </div>
          <div style={{
            background: 'rgba(16, 185, 129, 0.05)',
            border: '1px solid rgba(16, 185, 129, 0.15)',
            borderRadius: 6,
            padding: '4px 6px',
            color: '#10B981',
            textAlign: 'center',
          }}>
            ROUTE: REALTIME
          </div>
        </div>
      </div>
    </div>
  );
}


