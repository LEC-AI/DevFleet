import React, { useState, useEffect } from 'react';
import { listProjects, createMission, dispatchMission } from '../api/client';

/** The one extra card a member's scoped dashboard carries: queue work for
 *  their agents (tonight's backlog) or fire it off immediately. */
export default function AssignTask({ memberId, onDone }) {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState('');
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [priority, setPriority] = useState(3);
  const [type, setType] = useState('fix');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [okMsg, setOkMsg] = useState('');

  // Only this member's own projects: assigning work into someone else's
  // confined workspace is exactly what per-member isolation forbids (and the
  // API now rejects it too).
  useEffect(() => {
    listProjects().then(ps => setProjects(ps.filter(p => p.owner === memberId))).catch(() => {});
  }, [memberId]);

  const assign = async (dispatchNow) => {
    if (!projectId || !title.trim()) { setErr('Pick a project and give the task a title'); return; }
    setBusy(true); setErr(''); setOkMsg('');
    try {
      const m = await createMission({
        project_id: projectId,
        title: title.trim(),
        detailed_prompt: prompt.trim() || title.trim(),
        priority: Number(priority),
        mission_type: type,
        assignee: memberId,
        tags: ['backlog'],
        auto_dispatch: !dispatchNow,
      });
      if (dispatchNow) await dispatchMission(m.id);
      setTitle(''); setPrompt('');
      setOkMsg(dispatchNow ? 'Dispatched.' : 'Queued for tonight.');
      onDone?.();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="card" style={{ marginBottom: 28 }}>
      <h3 className="card-title">Assign a task</h3>
      <div className="form-row">
        <select className="form-select" value={projectId} onChange={e => setProjectId(e.target.value)}>
          <option value="">Project…</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select className="form-select" value={type} onChange={e => setType(e.target.value)}>
          {['fix', 'implement', 'review', 'test', 'explore'].map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <select className="form-select" value={priority} onChange={e => setPriority(e.target.value)}>
          {[5, 4, 3, 2, 1, 0].map(p => <option key={p} value={p}>P{p}</option>)}
        </select>
      </div>
      <input className="form-input" placeholder="What needs doing"
             value={title} onChange={e => setTitle(e.target.value)} />
      <textarea className="form-textarea" rows={3}
                placeholder="Fuller instructions — a thin prompt gets a thin result"
                value={prompt} onChange={e => setPrompt(e.target.value)} />
      {err && <div className="error-banner">{err}</div>}
      {okMsg && <p className="text-dim">{okMsg}</p>}
      <div className="form-row">
        <button className="btn btn-primary" disabled={busy} onClick={() => assign(false)}>Queue for tonight</button>
        <button className="btn" disabled={busy} onClick={() => assign(true)}>Run now</button>
      </div>
    </div>
  );
}
