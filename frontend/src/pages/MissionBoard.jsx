import React, { useState, useEffect } from 'react';
import { listMissions, listProjects, createMission } from '../api/client';
import MissionCard from '../components/MissionCard';

const TABS = ['all', 'draft', 'queued', 'running', 'completed', 'failed'];

export default function MissionBoard({ navigate }) {
  const [missions, setMissions] = useState([]);
  const [projects, setProjects] = useState([]);
  const [activeTab, setActiveTab] = useState('all');
  const [filterProject, setFilterProject] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ project_id: '', title: '', detailed_prompt: '', acceptance_criteria: '', priority: 0, tags: '', model: 'claude-opus-4-6', mission_type: 'implement' });
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      const [m, p] = await Promise.all([listMissions(), listProjects()]);
      setMissions(m);
      setProjects(p);
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = missions.filter(m => {
    if (activeTab !== 'all' && m.status !== activeTab) return false;
    if (filterProject && m.project_id !== filterProject) return false;
    return true;
  });

  const counts = {};
  missions.forEach(m => {
    const key = filterProject ? (m.project_id === filterProject ? m.status : null) : m.status;
    if (key) counts[key] = (counts[key] || 0) + 1;
  });

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const tags = form.tags ? form.tags.split(',').map(t => t.trim()).filter(Boolean) : [];
      await createMission({ ...form, priority: Number(form.priority), tags });
      setForm({ project_id: '', title: '', detailed_prompt: '', acceptance_criteria: '', priority: 0, tags: '', model: 'claude-opus-4-6', mission_type: 'implement' });
      setShowModal(false);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Missions</h2>
          <p>{missions.length} total</p>
        </div>
        <div className="flex gap-8">
          <select className="form-select" value={filterProject} onChange={e => setFilterProject(e.target.value)} style={{ minWidth: 140 }}>
            <option value="">All Projects</option>
            {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>New Mission</button>
        </div>
      </div>

      {error && <div style={{ color: 'var(--danger)', marginBottom: 16 }}>{error}</div>}

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

      {filtered.length === 0 ? (
        <div className="empty-state">
          <h3>No missions {activeTab !== 'all' ? `with status "${activeTab}"` : 'yet'}</h3>
          <p>Create a mission to get your coding agents working</p>
        </div>
      ) : (
        <div className="flex flex-col gap-8">
          {filtered.map(m => (
            <MissionCard key={m.id} mission={m} onClick={() => navigate('mission', m.id)} />
          ))}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>New Mission</h3>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label className="form-label">Project</label>
                <select className="form-select" value={form.project_id} onChange={e => setForm({ ...form, project_id: e.target.value })} required>
                  <option value="">Select project...</option>
                  {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Title</label>
                <input className="form-input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Add user authentication endpoint" required />
              </div>
              <div className="form-group">
                <label className="form-label">Detailed Prompt</label>
                <textarea className="form-textarea" value={form.detailed_prompt} onChange={e => setForm({ ...form, detailed_prompt: e.target.value })} placeholder="Describe exactly what the agent should build..." rows={6} required style={{ fontFamily: 'var(--font-mono)', fontSize: 13 }} />
              </div>
              <div className="form-group">
                <label className="form-label">Acceptance Criteria (optional)</label>
                <textarea className="form-textarea" value={form.acceptance_criteria} onChange={e => setForm({ ...form, acceptance_criteria: e.target.value })} placeholder="- Tests pass\n- No lint errors" rows={3} />
              </div>
              <div className="flex gap-16">
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label">Model</label>
                  <select className="form-select" value={form.model} onChange={e => setForm({ ...form, model: e.target.value })}>
                    <option value="claude-opus-4-6">Opus 4.6</option>
                    <option value="claude-sonnet-4-6">Sonnet 4.6</option>
                    <option value="claude-haiku-4-5-20251001">Haiku 4.5</option>
                  </select>
                </div>
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label">Type</label>
                  <select className="form-select" value={form.mission_type} onChange={e => setForm({ ...form, mission_type: e.target.value })}>
                    <option value="full">Full Access</option>
                    <option value="implement">Implement</option>
                    <option value="review">Review</option>
                    <option value="test">Test</option>
                    <option value="explore">Explore</option>
                    <option value="fix">Fix</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-16">
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label">Priority (0-5)</label>
                  <input className="form-input" type="number" min={0} max={5} value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })} />
                </div>
                <div className="form-group" style={{ flex: 2 }}>
                  <label className="form-label">Tags (comma-separated)</label>
                  <input className="form-input" value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })} placeholder="backend, auth" />
                </div>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Mission</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
