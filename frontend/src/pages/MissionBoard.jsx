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
  const [form, setForm] = useState({ project_id: '', title: '', detailed_prompt: '', acceptance_criteria: '', priority: 0, tags: '', model: 'claude-opus-4-6', mission_type: 'implement', auto_dispatch: false, schedule_cron: '', depends_on: '' });
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
      const depends_on = form.depends_on ? form.depends_on.split(',').map(t => t.trim()).filter(Boolean) : [];
      const payload = {
        ...form,
        priority: Number(form.priority),
        tags,
        auto_dispatch: form.auto_dispatch ? 1 : 0,
        schedule_cron: form.schedule_cron || null,
        depends_on,
      };
      delete payload.depends_on_text;
      await createMission(payload);
      setForm({ project_id: '', title: '', detailed_prompt: '', acceptance_criteria: '', priority: 0, tags: '', model: 'claude-opus-4-6', mission_type: 'implement', auto_dispatch: false, schedule_cron: '', depends_on: '' });
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
              {/* Automation Section */}
              <div style={{
                marginTop: 8, padding: '14px 16px',
                background: 'rgba(218,119,86,0.04)', border: '1px solid rgba(218,119,86,0.1)',
                borderRadius: 'var(--radius-md)',
              }}>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--accent-text)', marginBottom: 12 }}>
                  Automation
                </div>

                {/* Auto-Dispatch Toggle */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>Auto-Dispatch</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Automatically dispatch when dependencies are met</div>
                  </div>
                  <label style={{ position: 'relative', width: 44, height: 24, cursor: 'pointer' }}>
                    <input type="checkbox" checked={form.auto_dispatch} onChange={e => setForm({ ...form, auto_dispatch: e.target.checked })}
                      style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
                    <span style={{
                      position: 'absolute', inset: 0, borderRadius: 12,
                      background: form.auto_dispatch ? 'var(--success)' : 'var(--bg-input)',
                      border: '1px solid ' + (form.auto_dispatch ? 'var(--success)' : 'var(--border)'),
                      transition: 'all 0.2s',
                    }}>
                      <span style={{
                        position: 'absolute', top: 2, left: form.auto_dispatch ? 22 : 2,
                        width: 18, height: 18, borderRadius: '50%', background: 'white',
                        transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                      }} />
                    </span>
                  </label>
                </div>

                {/* Schedule */}
                <div className="form-group" style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <label className="form-label" style={{ margin: 0 }}>Schedule (cron)</label>
                    {form.schedule_cron && (
                      <span style={{
                        fontSize: 9, fontWeight: 700, padding: '1px 6px',
                        background: 'rgba(234,179,8,0.1)', color: 'var(--warning)',
                        borderRadius: 'var(--radius-full)',
                      }}>{'\u23F0'} SCHEDULED</span>
                    )}
                  </div>
                  <input className="form-input" value={form.schedule_cron}
                    onChange={e => setForm({ ...form, schedule_cron: e.target.value })}
                    placeholder="*/30 * * * *  (every 30 min)"
                    style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }} />
                  <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
                    Format: min hour day month weekday — e.g. "0 9 * * 1-5" = 9am weekdays
                  </div>
                </div>

                {/* Dependencies */}
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Depends On (mission IDs)</label>
                  <input className="form-input" value={form.depends_on}
                    onChange={e => setForm({ ...form, depends_on: e.target.value })}
                    placeholder="Paste mission IDs, comma-separated"
                    style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }} />
                  <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
                    This mission won't dispatch until all dependencies complete
                  </div>
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
