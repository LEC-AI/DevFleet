import React, { useState, useEffect } from 'react';
import { getProject, listMissions } from '../api/client';
import MissionCard from '../components/MissionCard';
import StatusBadge from '../components/StatusBadge';

function timeAgo(dateStr) {
  if (!dateStr) return '';
  let normalized = dateStr;
  if (!normalized.includes('T')) normalized = normalized.replace(' ', 'T');
  if (!normalized.endsWith('Z') && !normalized.includes('+')) normalized += 'Z';
  const ts = new Date(normalized).getTime();
  if (isNaN(ts)) return '';
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const TABS = ['all', 'draft', 'running', 'completed', 'failed'];

export default function ProjectDetail({ id, navigate }) {
  const [project, setProject] = useState(null);
  const [missions, setMissions] = useState([]);
  const [activeTab, setActiveTab] = useState('all');
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      const [p, m] = await Promise.all([
        getProject(id),
        listMissions({ project_id: id }),
      ]);
      setProject(p);
      setMissions(m);
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => { load(); }, [id]);

  if (error) return <div className="empty-state"><h3>Error</h3><p>{error}</p></div>;
  if (!project) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
      <div className="loading-spinner" />
    </div>
  );

  const filtered = missions.filter(m => activeTab === 'all' || m.status === activeTab);
  const counts = {};
  missions.forEach(m => { counts[m.status] = (counts[m.status] || 0) + 1; });

  return (
    <div>
      <button className="back-btn" onClick={() => navigate('projects')}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 12H5M12 19l-7-7 7-7" />
        </svg>
        Back to Projects
      </button>

      {/* Project header */}
      <div style={{ marginBottom: 28 }}>
        <div className="flex justify-between items-center" style={{ marginBottom: 8 }}>
          <h2 style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.02em' }}>{project.name}</h2>
          <button className="btn btn-primary" onClick={() => navigate('missions')}>
            New Mission
          </button>
        </div>
        <div className="text-sm font-mono text-muted" style={{ marginBottom: 6 }}>{project.path}</div>
        {project.description && <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{project.description}</p>}
      </div>

      {/* Stats row */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <div className="stats-card">
          <div className="stats-label">Total Missions</div>
          <div className="stats-value">{missions.length}</div>
        </div>
        <div className="stats-card">
          <div className="stats-label">Completed</div>
          <div className="stats-value" style={{ color: 'var(--success)' }}>{counts.completed || 0}</div>
        </div>
        <div className="stats-card">
          <div className="stats-label">Running</div>
          <div className="stats-value" style={{ color: counts.running ? 'var(--warning)' : 'var(--text-dim)' }}>{counts.running || 0}</div>
        </div>
        <div className="stats-card">
          <div className="stats-label">Failed</div>
          <div className="stats-value" style={{ color: counts.failed ? 'var(--danger)' : 'var(--text-dim)' }}>{counts.failed || 0}</div>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="filter-tabs">
        {TABS.map(tab => (
          <button key={tab} className={`filter-tab ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)}>
            {tab}
            {tab === 'all' ? (
              <span className="count">{missions.length}</span>
            ) : counts[tab] ? (
              <span className="count">{counts[tab]}</span>
            ) : null}
          </button>
        ))}
      </div>

      {/* Mission list */}
      {filtered.length === 0 ? (
        <div className="empty-state">
          <h3>No missions {activeTab !== 'all' ? `with status "${activeTab}"` : 'yet'}</h3>
          <p>Create a mission to get agents working on this project</p>
          <button className="btn btn-primary" onClick={() => navigate('missions')}>New Mission</button>
        </div>
      ) : (
        <div className="flex flex-col gap-8">
          {filtered.map(m => (
            <MissionCard key={m.id} mission={m} onClick={() => navigate('mission', m.id)} />
          ))}
        </div>
      )}
    </div>
  );
}
