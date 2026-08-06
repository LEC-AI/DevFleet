import React, { useState, useEffect } from 'react';
import { getDashboardStats, listTeam } from '../api/client';

const NAV = [
  { id: 'dashboard', label: 'Master Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1' },
  { id: 'projects', label: 'Projects', icon: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z' },
  { id: 'reports', label: 'Reports', icon: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
];

/** Initials for the tab avatar: "Mohammed Kaif Kohari" → "MK". */
function initials(name) {
  const parts = (name || '').trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '?';
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
}

export default function Sidebar({ activePage, activeId, navigate }) {
  const [runningAgents, setRunningAgents] = useState(0);
  const [team, setTeam] = useState([]);

  useEffect(() => {
    const poll = async () => {
      try {
        const stats = await getDashboardStats();
        setRunningAgents(stats.running_agents || 0);
      } catch {}
      try {
        setTeam(await listTeam());
      } catch {}
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);

  const isActive = runningAgents > 0;

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h1>Claude <span className="logo-gradient">DevFleet</span></h1>
        <p>Coding Team Orchestrator</p>
        <p className="powered-by">Powered by Claude Code</p>
      </div>

      <nav className="sidebar-nav">
        {NAV.map(item => (
          <button
            key={item.id}
            className={`nav-item ${activePage === item.id ? 'active' : ''}`}
            onClick={() => navigate(item.id)}
          >
            <span className="nav-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d={item.icon} />
              </svg>
            </span>
            <span className="nav-label">{item.label}</span>
          </button>
        ))}

        {team.length > 0 && <div className="nav-section-label">Team</div>}
        {team.map(m => (
          <button
            key={m.id}
            className={`nav-item nav-item--member ${activePage === 'member' && activeId === m.id ? 'active' : ''}`}
            onClick={() => navigate('member', m.id)}
            title={`${m.display_name || m.name} — ${m.running} running, ${m.queued} queued`}
          >
            <span className="nav-avatar" style={m.accent ? { background: m.accent } : undefined}>
              {initials(m.display_name || m.name)}
            </span>
            <span className="nav-label">{m.display_name || m.name}</span>
            {m.running > 0
              ? <span className="nav-badge nav-badge--running">{m.running}</span>
              : m.queued > 0 ? <span className="nav-badge">{m.queued}</span> : null}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className={`agent-indicator ${isActive ? 'agents-active' : ''}`}>
          <div className="agent-ring-wrapper">
            {isActive && <div className="agent-pulse-ring" />}
            <div className={`agent-dot ${runningAgents === 0 ? 'idle' : ''}`} />
          </div>
          <div className="agent-status-text">
            <span className="agent-count">{runningAgents}</span>
            {' '}agent{runningAgents !== 1 ? 's' : ''} running
          </div>
        </div>
        <div className="sidebar-version">v2.0</div>
      </div>
    </aside>
  );
}
