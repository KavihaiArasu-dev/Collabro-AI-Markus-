import { FolderKanban, Plus, GitBranch, Star } from 'lucide-react';

/* Placeholder pages for remaining sidebar items */

export function ProjectsPage() {
  return (
    <div style={{ animation: 'fadeIn 0.5s ease' }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: 4 }}>Projects</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Create, open, clone, import, and manage your projects
        </p>
      </div>
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: 16,
      }}>
        <div className="glass-card" style={{
          padding: 24, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 12,
          minHeight: 160, cursor: 'pointer', border: '2px dashed rgba(255,255,255,0.08)',
          borderRadius: 20, transition: 'all 0.3s',
        }}>
          <Plus size={28} color="var(--text-muted)" />
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>New Project</span>
        </div>
        {['Markus AI', 'OmniRoute Gateway', 'Portfolio Website'].map(name => (
          <div key={name} className="glass-card" style={{ padding: 24, cursor: 'pointer' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
              <FolderKanban size={20} color="var(--ai-cyan)" />
              <span style={{ fontSize: '1rem', fontWeight: 600 }}>{name}</span>
            </div>
            <div style={{ display: 'flex', gap: 8, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <GitBranch size={12} /> main
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Star size={12} /> Active
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function KnowledgePage() {
  return (
    <div style={{ animation: 'fadeIn 0.5s ease' }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: 4 }}>Knowledge Base</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Upload and search your documents — PDF, Markdown, Word, Text, Code repositories
        </p>
      </div>
      <div className="glass-card" style={{ padding: 40, textAlign: 'center' }}>
        <div style={{
          width: 64, height: 64, borderRadius: 16,
          background: 'rgba(99,102,241,0.1)',
          border: '1px solid rgba(99,102,241,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 16px',
        }}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#6366F1" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <line x1="9" y1="15" x2="15" y2="15" />
          </svg>
        </div>
        <div style={{ fontSize: '1rem', fontWeight: 500, marginBottom: 6 }}>Drop files here</div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          or click to browse — supports PDF, MD, DOCX, TXT, and code files
        </div>
      </div>
    </div>
  );
}

export function PluginsPage() {
  return (
    <div style={{ animation: 'fadeIn 0.5s ease' }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: 4 }}>Plugins</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Third-party extensions, agent extensions, and developer tools
        </p>
      </div>
      <div className="glass-card" style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
        Plugin marketplace coming soon — extensible through the plugin system
      </div>
    </div>
  );
}

export function WorkflowPage() {
  return (
    <div style={{ animation: 'fadeIn 0.5s ease' }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: 4 }}>Workflow Builder</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Visual automation — task chains, conditional execution, triggers
        </p>
      </div>
      <div className="glass-card" style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
        Drag-and-drop workflow builder coming in Phase 3
      </div>
    </div>
  );
}

export function TerminalPage() {
  return (
    <div style={{ animation: 'fadeIn 0.5s ease', height: 'calc(100vh - 48px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 4 }}>Terminal</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
          AI-assisted terminal overlay
        </p>
      </div>
      <div className="glass-card" style={{
        flex: 1,
        padding: 20,
        fontFamily: 'var(--font-code)',
        fontSize: '0.85rem',
        color: 'var(--ai-emerald)',
        overflow: 'auto',
      }}>
        <div style={{ opacity: 0.5 }}>markus@local:~$</div>
        <div style={{ color: 'var(--text-muted)', marginTop: 8 }}>
          Terminal integration coming in Phase 3 — AI assistance directly in your terminal
        </div>
      </div>
    </div>
  );
}

export function SettingsPage() {
  const SECTIONS = [
    { label: 'General', items: [
      { name: 'Theme', value: 'Dark', type: 'select' },
      { name: 'Language', value: 'English', type: 'select' },
    ]},
    { label: 'AI Gateway', items: [
      { name: 'OmniRoute URL', value: 'http://localhost:20128/v1', type: 'input' },
      { name: 'API Key', value: '•••••••••', type: 'password' },
      { name: 'Default Route', value: 'auto', type: 'select' },
    ]},
    { label: 'Privacy', items: [
      { name: 'Local-first mode', value: 'Enabled', type: 'toggle' },
      { name: 'Send analytics', value: 'Disabled', type: 'toggle' },
    ]},
  ];

  return (
    <div style={{ animation: 'fadeIn 0.5s ease' }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: 4 }}>Settings</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Configure Markus AI and connected services
        </p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 640 }}>
        {SECTIONS.map(section => (
          <div key={section.label}>
            <h3 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              {section.label}
            </h3>
            <div className="glass-card" style={{ overflow: 'hidden' }}>
              {section.items.map((item, i) => (
                <div key={item.name} style={{
                  padding: '14px 20px',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  borderBottom: i < section.items.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                }}>
                  <span style={{ fontSize: '0.88rem' }}>{item.name}</span>
                  <span style={{
                    fontSize: '0.82rem', color: 'var(--text-muted)',
                    fontFamily: 'var(--font-code)',
                    padding: '3px 10px',
                    borderRadius: 6,
                    background: 'rgba(255,255,255,0.04)',
                  }}>
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
