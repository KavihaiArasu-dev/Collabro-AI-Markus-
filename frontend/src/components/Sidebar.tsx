import { useState, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, MessageSquare, Bot, FolderKanban, BookOpen,
  Puzzle, GitBranch, Terminal, Settings, ChevronLeft, ChevronRight,
  Search, Sparkles,
} from 'lucide-react';

/* ═══════════════════════════════════════════════════════════
   SIDEBAR — Collapsible navigation (§11)
   
   Collapsed: icons only
   Expanded: icons + labels + search
   Hover: expand smoothly
   ═══════════════════════════════════════════════════════════ */

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const NAV_ITEMS = [
  { path: '/',           icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/chat',       icon: MessageSquare,   label: 'Chat' },
  { path: '/agents',     icon: Bot,             label: 'Agents' },
  { path: '/projects',   icon: FolderKanban,    label: 'Projects' },
  { path: '/knowledge',  icon: BookOpen,        label: 'Knowledge' },
  { path: '/plugins',    icon: Puzzle,           label: 'Plugins' },
  { path: '/workflow',   icon: GitBranch,       label: 'Workflow' },
  { path: '/terminal',   icon: Terminal,        label: 'Terminal' },
  { path: '/settings',   icon: Settings,        label: 'Settings' },
];

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const isActive = useCallback((path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  }, [location.pathname]);

  return (
    <aside
      style={{
        width: collapsed ? 72 : 260,
        minWidth: collapsed ? 72 : 260,
        height: '100vh',
        background: 'rgba(5, 7, 13, 0.95)',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        position: 'relative',
        zIndex: 50,
        backdropFilter: 'blur(30px)',
        overflow: 'hidden',
      }}
    >
      {/* Logo */}
      <div style={{
        padding: collapsed ? '20px 0' : '20px 20px',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        justifyContent: collapsed ? 'center' : 'flex-start',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        minHeight: 68,
      }}>
        <div style={{
          width: 36,
          height: 36,
          borderRadius: 10,
          background: 'linear-gradient(135deg, #00E5FF, #3B82F6, #8B5CF6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          <Sparkles size={20} color="white" />
        </div>
        {!collapsed && (
          <div style={{ overflow: 'hidden', whiteSpace: 'nowrap' }}>
            <div style={{
              fontFamily: 'var(--font-heading)',
              fontSize: '1.1rem',
              fontWeight: 700,
              background: 'linear-gradient(135deg, #00E5FF, #3B82F6, #8B5CF6)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: '0.05em',
            }}>MARKUS</div>
            <div style={{
              fontSize: '0.65rem',
              color: 'var(--text-muted)',
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
            }}>AI Operating System</div>
          </div>
        )}
      </div>

      {/* Search (expanded only) */}
      {!collapsed && (
        <div style={{ padding: '12px 16px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 12px',
            background: 'rgba(255,255,255,0.04)',
            borderRadius: 10,
            border: '1px solid rgba(255,255,255,0.06)',
          }}>
            <Search size={14} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Search..."
              style={{
                background: 'none',
                border: 'none',
                outline: 'none',
                color: 'var(--text-secondary)',
                fontSize: '0.8rem',
                fontFamily: 'var(--font-body)',
                width: '100%',
              }}
            />
            <kbd style={{
              fontSize: '0.6rem',
              padding: '2px 6px',
              borderRadius: 4,
              background: 'rgba(255,255,255,0.06)',
              color: 'var(--text-muted)',
              border: '1px solid rgba(255,255,255,0.08)',
            }}>⌘K</kbd>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav style={{
        flex: 1,
        padding: collapsed ? '12px 0' : '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        overflowY: 'auto',
      }}>
        {NAV_ITEMS.map(item => {
          const active = isActive(item.path);
          const hovered = hoveredItem === item.path;
          const Icon = item.icon;

          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              onMouseEnter={() => setHoveredItem(item.path)}
              onMouseLeave={() => setHoveredItem(null)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: collapsed ? '12px 0' : '10px 14px',
                justifyContent: collapsed ? 'center' : 'flex-start',
                background: active
                  ? 'rgba(0, 229, 255, 0.08)'
                  : hovered
                    ? 'rgba(255, 255, 255, 0.04)'
                    : 'transparent',
                border: 'none',
                borderRadius: collapsed ? 0 : 10,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                position: 'relative',
                color: active ? '#00E5FF' : hovered ? 'var(--text-primary)' : 'var(--text-muted)',
                width: '100%',
              }}
            >
              {/* Active indicator */}
              {active && (
                <div style={{
                  position: 'absolute',
                  left: 0,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: 3,
                  height: 20,
                  borderRadius: '0 3px 3px 0',
                  background: 'linear-gradient(180deg, #00E5FF, #3B82F6)',
                }} />
              )}

              <Icon size={20} style={{ flexShrink: 0, transition: 'transform 0.2s ease', transform: hovered ? 'rotate(3deg)' : 'none' }} />

              {!collapsed && (
                <span style={{
                  fontSize: '0.85rem',
                  fontWeight: active ? 500 : 400,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                }}>
                  {item.label}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '16px',
          background: 'none',
          border: 'none',
          borderTop: '1px solid rgba(255,255,255,0.06)',
          color: 'var(--text-muted)',
          cursor: 'pointer',
          transition: 'color 0.2s',
        }}
        onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
        onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
      >
        {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
      </button>
    </aside>
  );
}
