import { useState, useEffect } from 'react';
import { Bot, Zap, Code, Search, FileText, Palette, Cog, Brain, Shield } from 'lucide-react';

/* ═══════════════════════════════════════════════════════════
   AGENTS PAGE — Multi-Agent View (§13)
   
   Each agent has its own card showing:
   Status, Current task, Progress, Latency, Memory usage,
   Routing policy (which OmniRoute alias)
   Active agent glows, inactive remain dim.
   ═══════════════════════════════════════════════════════════ */

interface AgentInfo {
  type: string;
  name: string;
  description: string;
  icon: any;
  color: string;
  route: string;
  status: string;
  tasks_completed: number;
}

const AGENT_DEFS: AgentInfo[] = [
  { type: 'coder',         name: 'Coder',         description: 'Implementation, refactoring, optimization',       icon: Code,       color: '#FF8A00', route: '/coding', status: 'idle', tasks_completed: 0 },
  { type: 'architect',     name: 'Architect',     description: 'Project architecture, API & database design',     icon: Cog,        color: '#8B5CF6', route: '/smart',  status: 'idle', tasks_completed: 0 },
  { type: 'reviewer',      name: 'Reviewer',      description: 'Code, security, and performance review',          icon: Shield,     color: '#3B82F6', route: '/coding', status: 'idle', tasks_completed: 0 },
  { type: 'debugger',      name: 'Debugger',      description: 'Bugs, runtime errors, stack traces',              icon: Zap,        color: '#EF4444', route: '/smart',  status: 'idle', tasks_completed: 0 },
  { type: 'researcher',    name: 'Researcher',    description: 'Documentation, libraries, best practices',        icon: Search,     color: '#6366F1', route: 'auto',    status: 'idle', tasks_completed: 0 },
  { type: 'documentation', name: 'Documentation', description: 'README, API docs, technical reports',              icon: FileText,   color: '#10B981', route: 'auto',    status: 'idle', tasks_completed: 0 },
  { type: 'ui_ux',         name: 'UI/UX',         description: 'Interfaces, design systems, accessibility',       icon: Palette,    color: '#00E5FF', route: 'auto',    status: 'idle', tasks_completed: 0 },
  { type: 'automation',    name: 'Automation',     description: 'Scheduled tasks, CI/CD, workflows',               icon: Cog,        color: '#FACC15', route: '/fast',   status: 'idle', tasks_completed: 0 },
  { type: 'memory',        name: 'Memory',         description: 'Conversations, context, coding style',            icon: Brain,      color: '#F59E0B', route: '/fast',   status: 'idle', tasks_completed: 0 },
];

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>(AGENT_DEFS);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/agents/');
        if (res.ok) {
          const data = await res.json();
          if (data.agents && data.agents.length > 0) {
            setAgents(prev => prev.map(def => {
              const live = data.agents.find((a: any) => a.type === def.type);
              return live ? { ...def, ...live } : def;
            }));
          }
        }
      } catch { /* Backend not running */ }
    };
    fetchAgents();
    const interval = setInterval(fetchAgents, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ animation: 'fadeIn 0.5s ease' }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: 4 }}>Agents</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Multi-Agent System — {agents.length} specialized agents available
        </p>
      </div>

      {/* Workflow Pipeline (§14) */}
      <div className="glass-card" style={{
        padding: '20px 24px',
        marginBottom: 28,
        display: 'flex',
        alignItems: 'center',
        gap: 0,
        overflowX: 'auto',
      }}>
        {['Idea', 'Planner', 'Architect', 'Research', 'Coder', 'Reviewer', 'Debugger', 'Deploy'].map((step, i, arr) => (
          <div key={step} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{
              padding: '6px 14px',
              borderRadius: 8,
              background: i === 0 ? 'rgba(0,229,255,0.1)' : 'rgba(255,255,255,0.04)',
              border: `1px solid ${i === 0 ? 'rgba(0,229,255,0.3)' : 'rgba(255,255,255,0.06)'}`,
              fontSize: '0.75rem',
              fontWeight: 500,
              color: i === 0 ? '#00E5FF' : 'var(--text-muted)',
              whiteSpace: 'nowrap',
            }}>
              {step}
            </div>
            {i < arr.length - 1 && (
              <div style={{
                width: 24,
                height: 1,
                background: 'rgba(255,255,255,0.1)',
                margin: '0 4px',
              }} />
            )}
          </div>
        ))}
      </div>

      {/* Agent Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gap: 16,
      }}>
        {agents.map((agent, i) => (
          <div
            key={agent.type}
            className="glass-card"
            style={{
              padding: '22px 24px',
              animation: `fadeIn 0.4s ease ${i * 0.05}s both`,
              transition: 'all 0.3s',
              borderColor: agent.status === 'active' ? `${agent.color}40` : undefined,
              boxShadow: agent.status === 'active' ? `0 0 30px ${agent.color}20` : undefined,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 14 }}>
              <div style={{
                width: 42, height: 42, borderRadius: 12,
                background: `${agent.color}15`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                border: `1px solid ${agent.color}30`,
                flexShrink: 0,
              }}>
                <agent.icon size={20} color={agent.color} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: '1rem', fontWeight: 600,
                  display: 'flex', alignItems: 'center', gap: 8,
                }}>
                  {agent.name}
                  <span style={{
                    width: 7, height: 7, borderRadius: '50%',
                    background: agent.status === 'active' ? agent.color : 'rgba(255,255,255,0.15)',
                    boxShadow: agent.status === 'active' ? `0 0 8px ${agent.color}` : 'none',
                    display: 'inline-block',
                  }} />
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>
                  {agent.description}
                </div>
              </div>
            </div>

            {/* Meta info */}
            <div style={{
              display: 'flex', gap: 12, flexWrap: 'wrap',
              fontSize: '0.72rem', fontFamily: 'var(--font-code)',
            }}>
              <div style={{
                padding: '3px 8px', borderRadius: 6,
                background: `${agent.color}12`,
                color: agent.color,
                border: `1px solid ${agent.color}25`,
              }}>
                route: {agent.route}
              </div>
              <div style={{
                padding: '3px 8px', borderRadius: 6,
                background: 'rgba(255,255,255,0.03)',
                color: 'var(--text-muted)',
                border: '1px solid rgba(255,255,255,0.06)',
              }}>
                status: {agent.status}
              </div>
              <div style={{
                padding: '3px 8px', borderRadius: 6,
                background: 'rgba(255,255,255,0.03)',
                color: 'var(--text-muted)',
                border: '1px solid rgba(255,255,255,0.06)',
              }}>
                tasks: {agent.tasks_completed}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
