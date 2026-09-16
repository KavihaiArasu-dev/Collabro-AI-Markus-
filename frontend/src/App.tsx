import { useState, useEffect } from 'react';
import ParticleField from './components/ParticleField';
import VoiceVisionHUD from './pages/VoiceVisionHUD';
import { AIStateProvider } from './context/AIStateContext';
import './index.css';

/* ═══════════════════════════════════════════════════════════
   MARKUS AI — Pure Voice & Vision HUD Operating System
   
   Features:
   - Floating interactive AI Orb (Mind Core)
   - Facial Emotion & Vision Tracking HUD
   - Real-time Mic Speech Command Execution
   - Background Multi-Agent Orchestration & OmniRoute Routing
   ═══════════════════════════════════════════════════════════ */

const LOADING_STAGES = [
  'Initializing Neural Core',
  'Calibrating Audio & Voice Stream',
  'Initializing Vision & Facial Emotion Engine',
  'Starting Background Multi-Agent Mesh',
  'Connecting to OmniRoute Gateway',
  'System Ready',
];

function LoadingScreen({ onComplete }: { onComplete: () => void }) {
  const [stage, setStage] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const stageInterval = setInterval(() => {
      setStage(prev => {
        if (prev >= LOADING_STAGES.length - 1) {
          clearInterval(stageInterval);
          setTimeout(onComplete, 400);
          return prev;
        }
        return prev + 1;
      });
    }, 350);

    const progressInterval = setInterval(() => {
      setProgress(prev => Math.min(100, prev + 3));
    }, 25);

    return () => {
      clearInterval(stageInterval);
      clearInterval(progressInterval);
    };
  }, [onComplete]);

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: '#05070D',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      transition: 'opacity 0.5s ease',
      opacity: stage >= LOADING_STAGES.length - 1 ? 0 : 1,
    }}>
      {/* Glowing Hex / Star Core */}
      <div style={{
        width: 68,
        height: 68,
        borderRadius: 20,
        background: 'linear-gradient(135deg, #00E5FF, #3B82F6, #8B5CF6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 28,
        boxShadow: '0 0 70px rgba(0, 229, 255, 0.45)',
        animation: 'breathe 2s ease-in-out infinite',
      }}>
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
      </div>

      <div style={{
        fontFamily: 'var(--font-heading)',
        fontSize: '1.6rem',
        fontWeight: 800,
        background: 'linear-gradient(135deg, #00E5FF, #3B82F6, #8B5CF6)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        letterSpacing: '0.15em',
        marginBottom: 32,
      }}>
        MARKUS AI
      </div>

      {/* Stage indicators */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        marginBottom: 28,
        width: 280,
      }}>
        {LOADING_STAGES.map((s, i) => (
          <div key={s} style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            opacity: i <= stage ? 1 : 0.2,
            transition: 'opacity 0.3s ease',
          }}>
            <div style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: i < stage ? '#10B981' : i === stage ? '#00E5FF' : 'rgba(255,255,255,0.2)',
              boxShadow: i === stage ? '0 0 10px rgba(0, 229, 255, 0.6)' : 'none',
              transition: 'all 0.3s',
            }} />
            <span style={{
              fontSize: '0.75rem',
              fontFamily: 'var(--font-code)',
              color: i === stage ? '#00E5FF' : i < stage ? '#10B981' : 'var(--text-muted)',
              transition: 'color 0.3s',
            }}>
              {s}
            </span>
            {i === stage && (
              <span style={{
                fontSize: '0.65rem',
                color: 'var(--text-muted)',
                animation: 'pulse 1s infinite',
              }}>●</span>
            )}
          </div>
        ))}
      </div>

      {/* Progress bar */}
      <div style={{
        width: 280,
        height: 2,
        borderRadius: 1,
        background: 'rgba(255,255,255,0.06)',
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${progress}%`,
          background: 'linear-gradient(90deg, #00E5FF, #3B82F6, #8B5CF6)',
          borderRadius: 1,
          transition: 'width 0.1s linear',
        }} />
      </div>
    </div>
  );
}

export default function App() {
  const [loading, setLoading] = useState(true);

  return (
    <AIStateProvider>
      {loading && <LoadingScreen onComplete={() => setLoading(false)} />}
      
      <div style={{
        opacity: loading ? 0 : 1,
        transition: 'opacity 0.5s ease',
        height: '100vh',
        width: '100vw',
        position: 'relative',
        background: '#05070D',
        overflow: 'hidden',
      }}>
        {/* Background Particle Field */}
        <ParticleField particleCount={300} />

        {/* Ambient radial lighting */}
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'radial-gradient(ellipse at 50% 10%, rgba(0,229,255,0.04) 0%, transparent 60%), radial-gradient(ellipse at 80% 80%, rgba(139,92,246,0.04) 0%, transparent 50%)',
          pointerEvents: 'none',
          zIndex: 0,
        }} />

        {/* Pure Voice & Vision HUD */}
        <VoiceVisionHUD />
      </div>
    </AIStateProvider>
  );
}
