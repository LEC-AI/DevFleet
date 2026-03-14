import React, { useState, useEffect } from 'react';
import { listProjects, createProject, deleteProject } from '../api/client';

export default function Projects({ navigate }) {
  const [projects, setProjects] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ name: '', path: '', description: '' });
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      setProjects(await listProjects());
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await createProject(form);
      setForm({ name: '', path: '', description: '' });
      setShowModal(false);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this project and all its missions?')) return;
    try {
      await deleteProject(id);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Projects</h2>
          <p>Codebases your fleet works on</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          Add Project
        </button>
      </div>

      {error && <div style={{ color: 'var(--danger)', marginBottom: 16 }}>{error}</div>}

      {projects.length === 0 ? (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
          <h3>No projects yet</h3>
          <p>Add a codebase to start dispatching missions</p>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>Add Project</button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
          {projects.map(p => (
            <div key={p.id} className="card card-clickable" onClick={() => navigate('project', p.id)}>
              <div className="flex justify-between items-center" style={{ marginBottom: 12 }}>
                <h3 style={{ fontSize: 16, fontWeight: 600 }}>{p.name}</h3>
                <button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); handleDelete(p.id); }}>Delete</button>
              </div>
              <div className="text-sm text-muted font-mono" style={{ marginBottom: 8, wordBreak: 'break-all' }}>{p.path}</div>
              {p.description && <div className="text-sm" style={{ marginBottom: 12 }}>{p.description}</div>}
              <div className="flex gap-16 text-sm text-muted">
                <span>{p.mission_count || 0} missions</span>
                <span style={{ color: 'var(--success)' }}>{p.completed_count || 0} done</span>
                {p.running_count > 0 && <span style={{ color: 'var(--warning)' }}>{p.running_count} running</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Add Project</h3>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label className="form-label">Project Name</label>
                <input className="form-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="my-project" required />
              </div>
              <div className="form-group">
                <label className="form-label">Root Path</label>
                <input className="form-input font-mono" value={form.path} onChange={e => setForm({ ...form, path: e.target.value })} placeholder="/home/user/my-project" required />
              </div>
              <div className="form-group">
                <label className="form-label">Description (optional)</label>
                <textarea className="form-textarea" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Multi-tier AI agent system" rows={2} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
