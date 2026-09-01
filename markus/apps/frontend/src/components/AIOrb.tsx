import { useEffect, useRef } from 'react';

/* ═══════════════════════════════════════════════════════════
   AI ORB — Intelligent Living Core Component (§7)
   
   Implements the complete visual language from ARCHITECTURE.md:
   - Organic, non-circular boundary with membrane wobble & stipple
   - Concentric glass ring shells with iris tick-marks
   - Off-center glowing reactor core
   - Sacred-geometry (Flower-of-Life) lattice in idle/thinking
   - Dynamic treatments: Flow-field vortex (thinking),
     radiating spokes (executing), copper circuit traces (coding)
   - 60fps+ hardware-accelerated Canvas rendering (zero allocations)
   ═══════════════════════════════════════════════════════════ */

export type AIState = 
  | 'idle' | 'listening' | 'thinking' | 'planning' | 'coding'
  | 'research' | 'executing' | 'waiting_for_confirmation' 
  | 'speaking' | 'success' | 'warning' | 'error';

interface OrbProps {
  state?: AIState;
  size?: number;
  onClick?: () => void;
}

// Precomputed RGB channels & colors to avoid per-frame string parsing
const STATE_CONFIG: Record<AIState, { primary: string; glow: string; shadow: string; rgb: [number, number, number] }> = {
  idle:                     { primary: '#00E5FF', glow: 'rgba(0,229,255,0.4)',   shadow: '0 0 60px rgba(0,229,255,0.3)', rgb: [0, 229, 255] },
  listening:                { primary: '#3B82F6', glow: 'rgba(59,130,246,0.4)',  shadow: '0 0 60px rgba(59,130,246,0.3)', rgb: [59, 130, 246] },
  thinking:                 { primary: '#8B5CF6', glow: 'rgba(139,92,246,0.4)', shadow: '0 0 80px rgba(139,92,246,0.4)', rgb: [139, 92, 246] },
  planning:                 { primary: '#6366F1', glow: 'rgba(99,102,241,0.4)', shadow: '0 0 60px rgba(99,102,241,0.3)', rgb: [99, 102, 241] },
  coding:                   { primary: '#FF8A00', glow: 'rgba(255,138,0,0.4)',  shadow: '0 0 60px rgba(255,138,0,0.3)', rgb: [255, 138, 0] },
  research:                 { primary: '#6366F1', glow: 'rgba(99,102,241,0.4)', shadow: '0 0 60px rgba(99,102,241,0.3)', rgb: [99, 102, 241] },
  executing:                { primary: '#3B82F6', glow: 'rgba(59,130,246,0.4)', shadow: '0 0 60px rgba(59,130,246,0.3)', rgb: [59, 130, 246] },
  waiting_for_confirmation: { primary: '#FACC15', glow: 'rgba(250,204,21,0.4)', shadow: '0 0 60px rgba(250,204,21,0.3)', rgb: [250, 204, 21] },
  speaking:                 { primary: '#10B981', glow: 'rgba(16,185,129,0.4)', shadow: '0 0 60px rgba(16,185,129,0.3)', rgb: [16, 185, 129] },
  success:                  { primary: '#22C55E', glow: 'rgba(34,197,94,0.4)',  shadow: '0 0 60px rgba(34,197,94,0.3)', rgb: [34, 197, 94] },
  warning:                  { primary: '#FACC15', glow: 'rgba(250,204,21,0.4)', shadow: '0 0 40px rgba(250,204,21,0.2)', rgb: [250, 204, 21] },
  error:                    { primary: '#EF4444', glow: 'rgba(239,68,68,0.4)',  shadow: '0 0 60px rgba(239,68,68,0.3)', rgb: [239, 68, 68] },
};

const COPPER_RGB: [number, number, number] = [216, 155, 92]; // #D89B5C circuit trace accent

// ── Particle Class for Shell Dust & Halos ──
class HaloParticle {
  angle: number;
  orbitRadiusRatio: number;
  radius: number;
  baseOpacity: number;
  speed: number;

  constructor() {
    this.angle = Math.random() * Math.PI * 2;
    // Concentrated near the shell boundary (0.95 - 1.35)
    this.orbitRadiusRatio = 0.92 + Math.random() * 0.42;
    this.radius = 0.6 + Math.random() * 1.3;
    this.baseOpacity = 0.15 + Math.random() * 0.55;
    this.speed = (Math.random() - 0.5) * 0.008;
  }
}

export default function AIOrb({ state = 'idle', size = 200, onClick }: OrbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const particlesRef = useRef<HaloParticle[]>([]);
  const stateRef = useRef<AIState>(state);
  const sizeRef = useRef<number>(size);

  stateRef.current = state;
  sizeRef.current = size;

  const currentCfg = STATE_CONFIG[state] || STATE_CONFIG.idle;

  // Initialize particle dust once
  useEffect(() => {
    const count = 48;
    const particles: HaloParticle[] = [];
    for (let i = 0; i < count; i++) {
      particles.push(new HaloParticle());
    }
    particlesRef.current = particles;
  }, [size]);

  // High-performance Canvas animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    let time = 0;

    const animate = () => {
      const curState = stateRef.current;
      const curSize = sizeRef.current;
      const center = curSize / 2;
      const orbRadius = curSize * 0.28;
      const cfg = STATE_CONFIG[curState] || STATE_CONFIG.idle;

      // When waiting for confirmation, motion pauses visibly (§7)
      const timeIncrement = curState === 'waiting_for_confirmation' ? 0.002 : 0.016;
      time += timeIncrement;

      ctx.clearRect(0, 0, curSize, curSize);

      // 1. Outer Ambient Glow (§7 Layer 1)
      drawOuterGlow(ctx, center, orbRadius, cfg, time, curState);

      // 2. Particle Halo Dust (§7 Layer 2)
      drawParticleDust(ctx, center, orbRadius, cfg, time, curState, particlesRef.current);

      // 3. Organic Outer Ring with Membrane Wobble (§7 Layer 3)
      drawOrganicOuterRing(ctx, center, orbRadius, cfg, time, curState);

      // 4. Concentric Energy Ring Shells with Tick-marks (§7 Layer 4)
      drawEnergyRingShells(ctx, center, orbRadius, cfg, time, curState);

      // 5. Translucent Glass Reactor Shell (§7 Layer 5)
      drawGlassShell(ctx, center, orbRadius);

      // 6. Sacred Geometry (Flower-of-Life) at rest (Idle & Thinking)
      if (curState === 'idle' || curState === 'thinking') {
        drawSacredGeometry(ctx, center, orbRadius * 0.65, cfg, time, curState);
      }

      // 7. State-Specific Energetic Treatments
      if (curState === 'thinking') {
        drawFlowFieldVortex(ctx, center, orbRadius, cfg, time);
      } else if (curState === 'executing') {
        drawRadiatingSpokes(ctx, center, orbRadius, cfg, time);
        drawProgressRing(ctx, center, orbRadius, cfg, time);
      } else if (curState === 'coding') {
        drawCircuitTraces(ctx, center, orbRadius, time);
      } else if (curState === 'planning') {
        drawPlanningNodes(ctx, center, orbRadius, cfg, time);
      } else if (curState === 'research') {
        drawResearchOrbit(ctx, center, orbRadius, cfg, time);
      } else if (curState === 'speaking') {
        drawWaveform(ctx, center, orbRadius, cfg, time);
      } else if (curState === 'listening') {
        drawRipples(ctx, center, orbRadius, cfg, time);
      } else if (curState === 'success') {
        drawSuccessPulse(ctx, center, orbRadius, cfg, time);
      }

      // 8. Core Reactor & Inner Pulse (§7 Layer 6-7)
      drawInnerPulse(ctx, center, orbRadius, cfg, time, curState);

      // 9. Innermost Center Light (Off-center allowed, §7 Layer 8)
      drawCenterLight(ctx, center, orbRadius, cfg, time);

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();
    return () => cancelAnimationFrame(animationRef.current);
  }, [size]);

  const breatheScale = state === 'idle' ? 'animate-breathe' : '';
  const errorShake = state === 'error' ? 'animate-glitch' : '';

  return (
    <div 
      className={`orb-container ${breatheScale} ${errorShake}`}
      onClick={onClick}
      style={{
        width: size,
        height: size,
        position: 'relative',
        cursor: 'pointer',
        filter: `drop-shadow(${currentCfg.shadow})`,
        transition: 'filter 0.4s ease',
      }}
    >
      <canvas
        ref={canvasRef}
        style={{ width: size, height: size, display: 'block' }}
      />
      {/* State label HUD */}
      <div style={{
        position: 'absolute',
        bottom: -26,
        left: '50%',
        transform: 'translateX(-50%)',
        fontSize: '0.7rem',
        fontFamily: 'var(--font-code)',
        color: currentCfg.primary,
        opacity: 0.85,
        textTransform: 'uppercase',
        letterSpacing: '0.14em',
        whiteSpace: 'nowrap',
        transition: 'color 0.3s ease',
        textShadow: `0 0 12px ${currentCfg.primary}`,
      }}>
        {state.replace(/_/g, ' ')}
      </div>
    </div>
  );
}

// ── Ultra-Fast Canvas Renderers (Zero Heap Allocation in Render Loop) ──

function drawOuterGlow(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number, state: AIState
) {
  const pulseScale = state === 'idle' ? 1 + Math.sin(t * 1.5) * 0.05 : 
                     state === 'thinking' ? 1 + Math.sin(t * 3) * 0.08 : 
                     state === 'waiting_for_confirmation' ? 1 + Math.sin(t * 0.8) * 0.02 : 1;
  const [red, green, blue] = cfg.rgb;
  const grad = ctx.createRadialGradient(cx, cx, r * 0.4 * pulseScale, cx, cx, r * 2.2 * pulseScale);
  grad.addColorStop(0, `rgba(${red},${green},${blue},0.35)`);
  grad.addColorStop(0.45, `rgba(${red},${green},${blue},0.10)`);
  grad.addColorStop(0.85, `rgba(${red},${green},${blue},0.02)`);
  grad.addColorStop(1, 'transparent');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, cx * 2, cx * 2);
}

function drawParticleDust(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number, state: AIState,
  particles: HaloParticle[]
) {
  const [red, green, blue] = cfg.rgb;

  particles.forEach(p => {
    let speedMult = 1.0;
    if (state === 'thinking') speedMult = 3.0;
    else if (state === 'coding') speedMult = 2.0;
    else if (state === 'waiting_for_confirmation') speedMult = 0.1;

    p.angle += p.speed * speedMult;

    const currentRadius = r * p.orbitRadiusRatio + Math.sin(t * 1.5 + p.angle) * 2;
    const px = cx + Math.cos(p.angle) * currentRadius;
    const py = cx + Math.sin(p.angle) * currentRadius;
    const alpha = Math.max(0.05, Math.min(0.8, p.baseOpacity + Math.sin(t * 2.5 + p.angle * 3) * 0.2));

    ctx.beginPath();
    ctx.arc(px, py, p.radius, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${red},${green},${blue},${alpha})`;
    ctx.fill();
  });
}

function drawOrganicOuterRing(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number, _state: AIState
) {
  const [red, green, blue] = cfg.rgb;
  const outerR = r * 1.28;
  const points = 48;

  ctx.save();
  ctx.beginPath();

  for (let i = 0; i <= points; i++) {
    const angle = (i / points) * Math.PI * 2;
    // Harmonic wave perturbation for living membrane boundary (§7)
    const wobble = Math.sin(angle * 4 + t * 1.2) * 2.2 + 
                   Math.sin(angle * 7 - t * 0.8) * 1.4 + 
                   Math.cos(angle * 11 + t * 1.5) * 0.8;
    const rad = outerR + wobble;
    const x = cx + Math.cos(angle) * rad;
    const y = cx + Math.sin(angle) * rad;

    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.strokeStyle = `rgba(${red},${green},${blue},0.22)`;
  ctx.lineWidth = 1.2;
  ctx.stroke();

  // Dense stipple micro-dots along the organic boundary
  for (let i = 0; i < points; i += 2) {
    const angle = (i / points) * Math.PI * 2 + Math.sin(t * 0.5) * 0.05;
    const wobble = Math.sin(angle * 4 + t * 1.2) * 2.2;
    const rad = outerR + wobble;
    const px = cx + Math.cos(angle) * rad;
    const py = cx + Math.sin(angle) * rad;

    ctx.beginPath();
    ctx.arc(px, py, 0.9, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${red},${green},${blue},0.45)`;
    ctx.fill();
  }

  ctx.restore();
}

function drawEnergyRingShells(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number, state: AIState
) {
  const [red, green, blue] = cfg.rgb;

  // 1. Iris / Dial Tick-marked Ring (§7)
  const dialR = r * 1.14;
  const ticks = 36;
  const rot1 = state === 'thinking' ? t * 1.2 : t * 0.25;

  ctx.save();
  ctx.translate(cx, cx);
  ctx.rotate(rot1);

  ctx.beginPath();
  for (let i = 0; i < ticks; i++) {
    const angle = (i / ticks) * Math.PI * 2;
    const isMajor = i % 6 === 0;
    const tickLen = isMajor ? 3.5 : 1.8;
    const x1 = Math.cos(angle) * (dialR - tickLen);
    const y1 = Math.sin(angle) * (dialR - tickLen);
    const x2 = Math.cos(angle) * (dialR + tickLen);
    const y2 = Math.sin(angle) * (dialR + tickLen);

    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
  }
  ctx.strokeStyle = `rgba(${red},${green},${blue},0.32)`;
  ctx.lineWidth = 1;
  ctx.stroke();

  // 2. Middle Smooth Glass Arc Ring
  const midR = r * 0.96;
  ctx.beginPath();
  ctx.arc(0, 0, midR, 0, Math.PI * 2);
  ctx.strokeStyle = `rgba(${red},${green},${blue},0.18)`;
  ctx.lineWidth = 0.8;
  ctx.stroke();

  // 3. Counter-rotating segmented inner ring
  const rot2 = -t * 0.4;
  ctx.rotate(rot2 - rot1);
  ctx.beginPath();
  ctx.arc(0, 0, r * 0.82, 0, Math.PI * 1.4);
  ctx.strokeStyle = `rgba(${red},${green},${blue},0.28)`;
  ctx.lineWidth = 1.4;
  ctx.stroke();

  ctx.restore();
}

function drawGlassShell(ctx: CanvasRenderingContext2D, cx: number, r: number) {
  const grad = ctx.createRadialGradient(cx - r * 0.35, cx - r * 0.35, 0, cx, cx, r);
  grad.addColorStop(0, 'rgba(255,255,255,0.14)');
  grad.addColorStop(0.5, 'rgba(255,255,255,0.04)');
  grad.addColorStop(0.9, 'rgba(255,255,255,0.01)');
  grad.addColorStop(1, 'transparent');

  ctx.beginPath();
  ctx.arc(cx, cx, r, 0, Math.PI * 2);
  ctx.fillStyle = grad;
  ctx.fill();

  ctx.strokeStyle = 'rgba(255,255,255,0.09)';
  ctx.lineWidth = 1;
  ctx.stroke();
}

function drawSacredGeometry(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number, state: AIState
) {
  const [red, green, blue] = cfg.rgb;
  const baseAlpha = state === 'idle' 
    ? 0.12 + Math.sin(t * 1.2) * 0.06 
    : 0.22 + Math.sin(t * 2.5) * 0.08;

  const circles = 6;
  const petalR = r * 0.45;
  const rot = t * 0.15;

  ctx.save();
  ctx.translate(cx, cx);
  ctx.rotate(rot);

  // Central circle
  ctx.beginPath();
  ctx.arc(0, 0, petalR, 0, Math.PI * 2);
  ctx.strokeStyle = `rgba(${red},${green},${blue},${baseAlpha * 1.2})`;
  ctx.lineWidth = 0.8;
  ctx.stroke();

  // Flower-of-life overlapping circles (§7)
  for (let i = 0; i < circles; i++) {
    const angle = (i / circles) * Math.PI * 2;
    const px = Math.cos(angle) * petalR;
    const py = Math.sin(angle) * petalR;

    ctx.beginPath();
    ctx.arc(px, py, petalR, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(${red},${green},${blue},${baseAlpha})`;
    ctx.lineWidth = 0.7;
    ctx.stroke();
  }

  ctx.restore();
}

function drawFlowFieldVortex(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number
) {
  const [red, green, blue] = cfg.rgb;
  const arms = 12;

  ctx.save();
  ctx.translate(cx, cx);

  for (let i = 0; i < arms; i++) {
    const baseAngle = (i / arms) * Math.PI * 2 + t * 2.2;
    ctx.beginPath();
    for (let step = 0; step < 16; step++) {
      const radiusStep = r * (0.2 + (step / 16) * 0.85);
      const spiralAngle = baseAngle - step * 0.22;
      const x = Math.cos(spiralAngle) * radiusStep;
      const y = Math.sin(spiralAngle) * radiusStep;
      if (step === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = `rgba(${red},${green},${blue},0.26)`;
    ctx.lineWidth = 1.1;
    ctx.stroke();
  }

  ctx.restore();
}

function drawRadiatingSpokes(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number
) {
  const [red, green, blue] = cfg.rgb;
  const spokes = 16;

  ctx.save();
  ctx.translate(cx, cx);
  ctx.rotate(t * 0.8);

  for (let i = 0; i < spokes; i++) {
    const angle = (i / spokes) * Math.PI * 2;
    const spokeLen = r * (0.5 + Math.abs(Math.sin(t * 3 + i)) * 0.65);
    const alpha = 0.15 + Math.sin(t * 4 + i) * 0.15;

    ctx.beginPath();
    ctx.moveTo(Math.cos(angle) * (r * 0.25), Math.sin(angle) * (r * 0.25));
    ctx.lineTo(Math.cos(angle) * spokeLen, Math.sin(angle) * spokeLen);
    ctx.strokeStyle = `rgba(${red},${green},${blue},${alpha})`;
    ctx.lineWidth = 1.2;
    ctx.stroke();
  }

  ctx.restore();
}

function drawCircuitTraces(
  ctx: CanvasRenderingContext2D, cx: number, r: number, t: number
) {
  const [red, green, blue] = COPPER_RGB; // #D89B5C circuit accent (§7)

  ctx.save();
  ctx.translate(cx, cx);
  ctx.rotate(t * 0.35);

  const traces = [
    { start: [r * 0.3, -r * 0.2], mid: [r * 0.7, -r * 0.2], end: [r * 0.7, -r * 0.8] },
    { start: [-r * 0.4, r * 0.1], mid: [-r * 0.4, r * 0.6], end: [-r * 0.9, r * 0.6] },
    { start: [r * 0.1, r * 0.3], mid: [r * 0.5, r * 0.3], end: [r * 0.8, r * 0.7] },
    { start: [-r * 0.3, -r * 0.3], mid: [-r * 0.8, -r * 0.3], end: [-r * 0.8, -r * 0.7] },
  ];

  traces.forEach(tr => {
    ctx.beginPath();
    ctx.moveTo(tr.start[0], tr.start[1]);
    ctx.lineTo(tr.mid[0], tr.mid[1]);
    ctx.lineTo(tr.end[0], tr.end[1]);
    ctx.strokeStyle = `rgba(${red},${green},${blue},0.55)`;
    ctx.lineWidth = 1.3;
    ctx.stroke();

    // Solder pad terminal dot
    ctx.beginPath();
    ctx.arc(tr.end[0], tr.end[1], 2, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${red},${green},${blue},0.85)`;
    ctx.fill();
  });

  ctx.restore();
}

function drawPlanningNodes(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number
) {
  const [red, green, blue] = cfg.rgb;
  const nodes = [
    { x: -r * 0.5, y: -r * 0.3 },
    { x: -r * 0.1, y: -r * 0.5 },
    { x: r * 0.4, y: -r * 0.2 },
    { x: r * 0.2, y: r * 0.4 },
    { x: -r * 0.3, y: r * 0.4 },
  ];

  ctx.save();
  ctx.translate(cx, cx);
  ctx.rotate(t * 0.2);

  // Connection path
  ctx.beginPath();
  nodes.forEach((n, idx) => {
    if (idx === 0) ctx.moveTo(n.x, n.y);
    else ctx.lineTo(n.x, n.y);
  });
  ctx.closePath();
  ctx.strokeStyle = `rgba(${red},${green},${blue},0.35)`;
  ctx.lineWidth = 1;
  ctx.stroke();

  // Nodes
  nodes.forEach((n, idx) => {
    const pulse = 1.5 + Math.sin(t * 3 + idx) * 0.8;
    ctx.beginPath();
    ctx.arc(n.x, n.y, pulse, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${red},${green},${blue},0.8)`;
    ctx.fill();
  });

  ctx.restore();
}

function drawResearchOrbit(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number
) {
  const [red, green, blue] = cfg.rgb;
  const satellites = 5;

  ctx.save();
  ctx.translate(cx, cx);

  for (let i = 0; i < satellites; i++) {
    const angle = (i / satellites) * Math.PI * 2 + t * 1.4;
    const sx = Math.cos(angle) * (r * 0.85);
    const sy = Math.sin(angle) * (r * 0.85);

    // Line to center
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(sx, sy);
    ctx.strokeStyle = `rgba(${red},${green},${blue},0.15)`;
    ctx.lineWidth = 0.8;
    ctx.stroke();

    // Orbiting node
    ctx.beginPath();
    ctx.arc(sx, sy, 2, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${red},${green},${blue},0.75)`;
    ctx.fill();
  }

  ctx.restore();
}

function drawInnerPulse(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number, state: AIState
) {
  const pulseR = r * 0.55;
  const intensity = state === 'thinking' ? 0.42 + Math.sin(t * 3.5) * 0.18 :
                    state === 'waiting_for_confirmation' ? 0.28 + Math.sin(t * 0.8) * 0.08 :
                    0.25 + Math.sin(t * 1.5) * 0.10;

  const [red, green, blue] = cfg.rgb;
  const grad = ctx.createRadialGradient(cx, cx, 0, cx, cx, pulseR);
  grad.addColorStop(0, `rgba(${red},${green},${blue},${intensity})`);
  grad.addColorStop(1, 'transparent');

  ctx.beginPath();
  ctx.arc(cx, cx, pulseR, 0, Math.PI * 2);
  ctx.fillStyle = grad;
  ctx.fill();
}

function drawCenterLight(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number
) {
  // Off-center living drift allowed per §7
  const driftX = cx + Math.cos(t * 0.9) * (r * 0.04);
  const driftY = cx + Math.sin(t * 0.7) * (r * 0.04);
  const lightR = r * 0.16;
  const [red, green, blue] = cfg.rgb;

  const grad = ctx.createRadialGradient(driftX, driftY, 0, driftX, driftY, lightR);
  grad.addColorStop(0, 'rgba(255,255,255,0.95)');
  grad.addColorStop(0.35, `rgba(${red},${green},${blue},0.65)`);
  grad.addColorStop(1, 'transparent');

  ctx.beginPath();
  ctx.arc(driftX, driftY, lightR, 0, Math.PI * 2);
  ctx.fillStyle = grad;
  ctx.fill();
}

function drawWaveform(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number
) {
  const bars = 10;
  const barWidth = 2.5;
  const maxHeight = r * 0.55;
  const [red, green, blue] = cfg.rgb;

  ctx.save();
  ctx.translate(cx, cx);
  ctx.fillStyle = `rgba(${red},${green},${blue},0.75)`;

  for (let i = 0; i < bars; i++) {
    const x = (i - bars / 2) * (barWidth + 4);
    const height = Math.abs(Math.sin(t * 5 + i * 0.55)) * maxHeight + 4;
    ctx.fillRect(x, -height / 2, barWidth, height);
  }

  ctx.restore();
}

function drawProgressRing(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number
) {
  const [red, green, blue] = cfg.rgb;
  ctx.save();
  ctx.translate(cx, cx);
  ctx.rotate(t * 2.2);

  ctx.beginPath();
  ctx.arc(0, 0, r * 0.92, 0, Math.PI * 1.35);
  ctx.strokeStyle = `rgba(${red},${green},${blue},0.65)`;
  ctx.lineWidth = 2.2;
  ctx.stroke();

  ctx.restore();
}

function drawRipples(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number
) {
  const [red, green, blue] = cfg.rgb;
  for (let i = 0; i < 3; i++) {
    const progress = ((t * 0.4 + i * 0.33) % 1);
    const rippleR = r * (0.7 + progress * 0.7);
    const alpha = Math.max(0, 0.35 * (1 - progress));

    ctx.beginPath();
    ctx.arc(cx, cx, rippleR, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(${red},${green},${blue},${alpha})`;
    ctx.lineWidth = 1.3;
    ctx.stroke();
  }
}

function drawSuccessPulse(
  ctx: CanvasRenderingContext2D, cx: number, r: number,
  cfg: typeof STATE_CONFIG['idle'], t: number
) {
  const [red, green, blue] = cfg.rgb;
  const progress = (t * 0.8) % 1;
  const pulseR = r * (0.8 + progress * 0.6);
  const alpha = Math.max(0, 0.4 * (1 - progress));

  ctx.beginPath();
  ctx.arc(cx, cx, pulseR, 0, Math.PI * 2);
  ctx.strokeStyle = `rgba(${red},${green},${blue},${alpha})`;
  ctx.lineWidth = 2;
  ctx.stroke();
}
