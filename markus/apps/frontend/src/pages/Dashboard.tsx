import { useState, useEffect } from 'react';
import { Cpu, HardDrive, MemoryStick, Activity, Wifi, WifiOff, Bot, Clock, Zap, MonitorSpeaker } from 'lucide-react';
import AIOrb from '../components/AIOrb';
import PerceptionWidget from '../components/PerceptionWidget';

/* ═══════════════════════════════════════════════════════════
   DASHBOARD — Glass cards with system metrics (§12)
   
   Cards: CPU, RAM, GPU, LLM, Active Route, Latency,
          Memory, Projects, Active Agents, Recent Tasks
   ═══════════════════════════════════════════════════════════ */

import { useAIState, AIState } from '../context/AIStateContext';

const AI_STATES: AIState[] = ['idle', 'listening', 'thinking', 'planning', 'coding', 'research', 'executing', 'waiting_for_confirmation', 'speaking', 'success', 'warning', 'error'];

export default function Dashboard() {
  const { aiState: orbState, setAiState: setOrbState, isConnected } = useAIState();
  const [metrics, setMetrics] = useState({
    cpu: 23, ram: 45, gpu: 12, disk: 38,
    latency: 120, activeAgents: 0, recentTasks: 5,
  });
  const [gatewayConnected, setGatewayConnected] = useState(false);
  const [agents, setAgents] = useState<any[]>([]);

  // Fetch system metrics
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/system/metrics');
        if (res.ok) {
          const data = await res.json();
          setMetrics(m => ({
            ...m,
            cpu: data.cpu_percent || m.cpu,
            ram: data.ram_percent || m.ram,
            disk: data.disk_percent || m.disk,
          }));
        }
      } catch { /* Backend not running yet, use defaults */ }
    };

    const fetchGateway = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/models/status');
        if (res.ok) {
          const data = await res.json();
          setGatewayConnected(data.connected);
        }
      } catch { /* Backend not running */ }
    };

    const fetchAgents = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/agents/');
        if (res.ok) {
          const data = await res.json();
          setAgents(data.agents || []);
        }
      } catch { /* Backend not running */ }
    };

    fetchMetrics();
    fetchGateway();
    fetchAgents();
    const interval = setInterval(() => {
      fetchMetrics();
      fetchGateway();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Simulate metric changes for demo
  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(m => ({
        ...m,
        cpu: Math.max(5, Math.min(95, m.cpu + (Math.random() - 0.5) * 8)),
        ram: Math.max(20, Math.min(90, m.ram + (Math.random() - 0.5) * 3)),
        gpu: Math.max(0, Math.min(95, m.gpu + (Math.random() - 0.5) * 5)),
        latency: Math.max(50, Math.min(500, m.latency + (Math.random() - 0.5) * 40)),
      }));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ animation: 'fadeIn 0.5s ease' }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: 4 }}>Dashboard</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Markus AI Operating System — System Overview
        </p>
      </div>

      {/* Top section: Orb + State Selector */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 48,
        marginBottom: 40,
        flexWrap: 'wrap',
      }}>
        <AIOrb state={orbState} size={180} onClick={() => {
          const idx = AI_STATES.indexOf(orbState);
          setOrbState(AI_STATES[(idx + 1) % AI_STATES.length]);
        }} />

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 360 }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>
            AI State
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {AI_STATES.map(s => (
              <button
                key={s}
                onClick={() => setOrbState(s)}
                style={{
                  padding: '4px 10px',
                  borderRadius: 8,
                  border: orbState === s ? '1px solid rgba(0,229,255,0.4)' : '1px solid rgba(255,255,255,0.08)',
                  background: orbState === s ? 'rgba(0,229,255,0.1)' : 'rgba(255,255,255,0.03)',
                  color: orbState === s ? '#00E5FF' : 'var(--text-muted)',
                  fontSize: '0.7rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  fontFamily: 'var(--font-code)',
                }}
              >
                {s.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>
            Click the orb or select a state to preview animations
          </div>
        </div>

        {/* Perception & Face Emotion Widget */}
        <div style={{ minWidth: 320, maxWidth: 420, flex: 1 }}>
          <PerceptionWidget />
        </div>
      </div>

      {/* Metrics Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
        gap: 16,
        marginBottom: 32,
      }}>
        <MetricCard icon={<Cpu size={20} />} label="CPU" value={`${metrics.cpu.toFixed(1)}%`} color="#00E5FF" progress={metrics.cpu} />
        <MetricCard icon={<MemoryStick size={20} />} label="RAM" value={`${metrics.ram.toFixed(1)}%`} color="#3B82F6" progress={metrics.ram} />
        <MetricCard icon={<MonitorSpeaker size={20} />} label="GPU" value={`${metrics.gpu.toFixed(1)}%`} color="#8B5CF6" progress={metrics.gpu} />
        <MetricCard icon={<HardDrive size={20} />} label="Disk" value={`${metrics.disk.toFixed(1)}%`} color="#10B981" progress={metrics.disk} />
        <MetricCard
          icon={gatewayConnected ? <Wifi size={20} /> : <WifiOff size={20} />}
          label="OmniRoute"
          value={gatewayConnected ? 'Connected' : 'Offline'}
          color={gatewayConnected ? '#10B981' : '#EF4444'}
          subtitle="AI Gateway"
        />
        <MetricCard icon={<Zap size={20} />} label="Latency" value={`${metrics.latency.toFixed(0)}ms`} color="#FF8A00" subtitle="Gateway Response" />
        <MetricCard icon={<Bot size={20} />} label="Agents" value={`${agents.length || 9}`} color="#6366F1" subtitle="Available" />
        <MetricCard icon={<Clock size={20} />} label="Tasks" value={`${metrics.recentTasks}`} color="#FACC15" subtitle="Recent" />
      </div>

      {/* Agent Overview */}
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: 16 }}>Active Agents</h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
          gap: 12,
        }}>
          {(agents.length > 0 ? agents : DEFAULT_AGENTS).map((agent: any) => (
            <AgentCard key={agent.type || agent.name} agent={agent} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Metric Card ──
function MetricCard({ icon, label, value, color, progress, subtitle }: {
  icon: React.ReactNode; label: string; value: string; color: string;
  progress?: number; subtitle?: string;
}) {
  return (
    <div className="glass-card" style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ color, opacity: 0.9 }}>{icon}</div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{label}</span>
        </div>
        <span style={{
          fontSize: '1.1rem', fontWeight: 600,
          fontFamily: 'var(--font-numbers)', color,
        }}>{value}</span>
      </div>
      {progress !== undefined && (
        <div style={{
          height: 4, borderRadius: 2,
          background: 'rgba(255,255,255,0.06)',
          overflow: 'hidden',
        }}>
          <div style={{
            height: '100%',
            width: `${Math.min(100, progress)}%`,
            borderRadius: 2,
            background: color,
            transition: 'width 0.8s ease',
            boxShadow: `0 0 8px ${color}40`,
          }} />
        </div>
      )}
      {subtitle && (
        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{subtitle}</span>
      )}
    </div>
  );
}

// ── Agent Card ──
function AgentCard({ agent }: { agent: any }) {
  const AGENT_COLORS: Record<string, string> = {
    coder: '#FF8A00', architect: '#8B5CF6', reviewer: '#3B82F6',
    debugger: '#EF4444', researcher: '#6366F1', documentation: '#10B981',
    ui_ux: '#00E5FF', automation: '#FACC15', memory: '#F59E0B',
  };

  const color = AGENT_COLORS[agent.type || agent.name] || '#00E5FF';

  return (
    <div className="glass-card" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 14 }}>
      <div style={{
        width: 8, height: 8, borderRadius: '50%',
        background: agent.status === 'active' ? color : 'rgba(255,255,255,0.15)',
        boxShadow: agent.status === 'active' ? `0 0 12px ${color}80` : 'none',
        transition: 'all 0.3s',
      }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 500, textTransform: 'capitalize' }}>
          {(agent.type || agent.name || '').replace(/_/g, ' ')}
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-code)' }}>
          {agent.route || 'auto'} • {agent.status || 'idle'}
        </div>
      </div>
      <div style={{
        fontSize: '0.65rem', padding: '2px 8px', borderRadius: 6,
        background: 'rgba(255,255,255,0.04)',
        color: 'var(--text-muted)',
        fontFamily: 'var(--font-code)',
      }}>
        {agent.tasks_completed || 0} tasks
      </div>
    </div>
  );
}

// Default agents for display when backend isn't connected
const DEFAULT_AGENTS = [
  { type: 'coder', name: 'Coder', status: 'idle', route: '/coding', tasks_completed: 0 },
  { type: 'architect', name: 'Architect', status: 'idle', route: '/smart', tasks_completed: 0 },
  { type: 'reviewer', name: 'Reviewer', status: 'idle', route: '/coding', tasks_completed: 0 },
  { type: 'debugger', name: 'Debugger', status: 'idle', route: '/smart', tasks_completed: 0 },
  { type: 'researcher', name: 'Researcher', status: 'idle', route: 'auto', tasks_completed: 0 },
  { type: 'documentation', name: 'Documentation', status: 'idle', route: 'auto', tasks_completed: 0 },
  { type: 'ui_ux', name: 'UI/UX', status: 'idle', route: 'auto', tasks_completed: 0 },
  { type: 'automation', name: 'Automation', status: 'idle', route: '/fast', tasks_completed: 0 },
  { type: 'memory', name: 'Memory', status: 'idle', route: '/fast', tasks_completed: 0 },
];
