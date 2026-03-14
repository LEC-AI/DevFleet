import React, { useState, useEffect } from 'react';
import { listReports, listProjects } from '../api/client';
import ReportView from '../components/ReportView';

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

export default function Reports({ navigate }) {
  const [reports, setReports] = useState([]);
  const [projects, setProjects] = useState([]);
  const [filterProject, setFilterProject] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    Promise.all([listReports(), listProjects()]).then(([r, p]) => {
      setReports(r);
      setProjects(p);
    }).catch(() => {});
  }, []);

  const filtered = filterProject
    ? reports.filter(r => r.project_name === projects.find(p => p.id === filterProject)?.name)
    : reports;

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Reports</h2>
          <p>{reports.length} agent reports</p>
        </div>
        <select className="form-select" value={filterProject} onChange={e => setFilterProject(e.target.value)} style={{ minWidth: 140 }}>
          <option value="">All Projects</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
          <h3>No reports yet</h3>
          <p>Reports appear after agents complete missions</p>
        </div>
      ) : (
        <div className="flex flex-col gap-8">
          {filtered.map(r => (
            <div key={r.id}>
              <div
                className="card card-clickable"
                onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}
                style={{ padding: '14px 20px' }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>{r.mission_title}</div>
                    <div className="text-sm text-muted flex gap-12">
                      <span>{r.project_name}</span>
                      <span>{timeAgo(r.created_at)}</span>
                    </div>
                  </div>
                  <span className="text-muted" style={{ fontSize: 18 }}>
                    {expandedId === r.id ? '−' : '+'}
                  </span>
                </div>
              </div>
              {expandedId === r.id && (
                <div style={{ marginTop: 8, marginLeft: 16 }}>
                  <ReportView report={r} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
