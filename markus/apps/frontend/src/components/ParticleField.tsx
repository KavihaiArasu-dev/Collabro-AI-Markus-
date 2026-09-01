import { useEffect, useRef } from 'react';

/* ═══════════════════════════════════════════════════════════
   PARTICLE SYSTEM — High Performance Background Stars (§9)
   
   Batched Canvas API rendering (<0.5ms execution budget)
   ═══════════════════════════════════════════════════════════ */

interface ParticleFieldProps {
  particleCount?: number;
}

interface Star {
  x: number; y: number;
  vx: number; vy: number;
  size: number;
  opacity: number;
  baseOpacity: number;
}

export default function ParticleField({ particleCount = 120 }: ParticleFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    let animId: number;
    let w = window.innerWidth;
    let h = window.innerHeight;

    const resize = () => {
      w = window.innerWidth;
      h = window.innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener('resize', resize);

    const count = Math.min(particleCount, 120);
    const stars: Star[] = Array.from({ length: count }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.12,
      vy: (Math.random() - 0.5) * 0.12,
      size: 0.5 + Math.random() * 1.2,
      baseOpacity: 0.1 + Math.random() * 0.3,
      opacity: 0.1 + Math.random() * 0.3,
    }));

    let time = 0;

    const draw = () => {
      time += 0.008;
      ctx.clearRect(0, 0, w, h);

      // 1. Update and batch draw all stars in a single path
      ctx.beginPath();
      for (let i = 0; i < count; i++) {
        const s = stars[i];
        s.x += s.vx;
        s.y += s.vy;

        if (s.x < 0) s.x = w;
        else if (s.x > w) s.x = 0;
        if (s.y < 0) s.y = h;
        else if (s.y > h) s.y = 0;

        ctx.moveTo(s.x + s.size, s.y);
        ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
      }
      ctx.fillStyle = 'rgba(180, 220, 255, 0.22)';
      ctx.fill();

      // 2. Batch draw connection lines in a single stroke pass (distSq < 6400 -> dist < 80)
      ctx.beginPath();
      for (let i = 0; i < count; i++) {
        const si = stars[i];
        const maxJ = Math.min(i + 6, count);
        for (let j = i + 1; j < maxJ; j++) {
          const sj = stars[j];
          const dx = si.x - sj.x;
          const dy = si.y - sj.y;
          const distSq = dx * dx + dy * dy;
          if (distSq < 6400) {
            ctx.moveTo(si.x, si.y);
            ctx.lineTo(sj.x, sj.y);
          }
        }
      }
      ctx.strokeStyle = 'rgba(100, 160, 255, 0.035)';
      ctx.lineWidth = 0.6;
      ctx.stroke();

      animId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, [particleCount]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
        opacity: 0.6,
      }}
    />
  );
}
