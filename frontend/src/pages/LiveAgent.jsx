import React, { useState, useEffect, useRef } from 'react';
import { getSession, streamSession, cancelSession, startRemoteControl } from '../api/client';
import LiveOutput from '../components/LiveOutput';
import ReportView from '../components/ReportView';
import RemoteControlModal from '../components/RemoteControlModal';

export default function LiveAgent({ sessionId, navigate }) {
  const [session, setSession] = useState(null);
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState('running');
  const [elapsed, setElapsed] = useState(0);
  const [report, setReport] = useState(null);
  const [config, setConfig] = useState(null);
  const [finalCost, setFinalCost] = useState(null);
  const [finalTokens, setFinalTokens] = useState(null);
  const [remoteUrl, setRemoteUrl] = useState(null);
  const [startingRemote, setStartingRemote] = useState(false);
  const cleanupRef = useRef(null);
  const startRef = useRef(Date.now());

  useEffect(() => {
    if (!sessionId) return;

    const loadSession = async () => {
      try {
        const s = await getSession(sessionId);
        setSession(s);
        if (s.report) setReport(s.report);
        if (s.remote_url) setRemoteUrl(s.remote_url);
        if (s.total_cost_usd) setFinalCost(s.total_cost_usd);
        if (s.total_tokens) setFinalTokens(s.total_tokens);
        if (s.status !== 'running') {
          setStatus(s.status);
          if (s.output_log) setEvents([{ type: 'text', text: s.output_log }]);
          return;
        }

        // Connect to SSE stream
        cleanupRef.current = streamSession(sessionId, {
          onEvent: (evt) => {
            if (evt.type === 'config') {
              setConfig(evt);
              return;
            }
            setEvents(prev => [...prev, evt]);
          },
          onBackfill: (text) => setEvents([{ type: 'text', text }]),
          onDone: async (data) => {
            setStatus(data.status || 'completed');
            if (data.cost) setFinalCost(data.cost);
            if (data.tokens) setFinalTokens(data.tokens);
            // Reload session to get report
            try {
              const updated = await getSession(sessionId);
              if (updated.report) setReport(updated.report);
            } catch {}
          },
          onError: () => setStatus('failed'),
        });
      } catch {}
    };

    loadSession();

    return () => {
      if (cleanupRef.current) cleanupRef.current();
    };
  }, [sessionId]);

  // Timer
  useEffect(() => {
    if (status !== 'running') return;
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [status]);

  const handleCancel = async () => {
    try {
      await cancelSession(sessionId);
      setStatus('cancelled');
    } catch {}
  };

  const handleRemoteControl = async () => {
    setStartingRemote(true);
    try {
      const result = await startRemoteControl(sessionId);
      setRemoteUrl(result.url);
    } catch (e) {
      console.error('Remote control error:', e);
    } finally {
      setStartingRemote(false);
    }
  };

  const formatTime = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${String(sec).padStart(2, '0')}`;
  };

  return (
    <div>
      <button className="back-btn" onClick={() => session?.mission_id ? navigate('mission', session.mission_id) : navigate('missions')}>
        ← Back to Mission
      </button>

      <div className="page-header">
        <div>
          <h2>{session?.mission_title || 'Agent Session'}</h2>
          <div className="flex items-center gap-12 mt-16">
            <span className={`status-badge status-badge--${status}`}>{status}</span>
            {status === 'running' && (
              <span className="text-sm text-muted">{formatTime(elapsed)}</span>
            )}
            {session?.model && (
              <span className="tag">{session.model.replace('claude-', '').split('-')[0]}</span>
            )}
            {config?.max_budget_usd && (
              <span className="text-sm text-muted">Budget: ${config.max_budget_usd}</span>
            )}
            {config?.max_turns && (
              <span className="text-sm text-muted">Max turns: {config.max_turns}</span>
            )}
            {finalCost > 0 && (
              <span className="text-sm font-mono" style={{ color: 'var(--accent-text)' }}>
                Cost: ${finalCost.toFixed(4)}
              </span>
            )}
            {finalTokens > 0 && (
              <span className="text-sm font-mono text-muted">
                {(finalTokens / 1000).toFixed(1)}k tokens
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-8">
          {status === 'running' && (
            <>
              <button
                className="btn btn-remote"
                onClick={handleRemoteControl}
                disabled={startingRemote || !!remoteUrl}
                title="Take over from phone"
              >
                {startingRemote ? 'Starting...' : remoteUrl ? 'Remote Active' : 'Take Over'}
              </button>
              <button className="btn btn-danger" onClick={handleCancel}>Cancel Agent</button>
            </>
          )}
          {remoteUrl && status !== 'running' && (
            <a href={remoteUrl} target="_blank" rel="noopener noreferrer" className="btn btn-remote">
              Open Remote
            </a>
          )}
        </div>
      </div>

      {remoteUrl && status === 'running' && (
        <div className="remote-control-banner" onClick={() => setRemoteUrl(null)}>
          <span>Remote control active — </span>
          <a href={remoteUrl} target="_blank" rel="noopener noreferrer">{remoteUrl}</a>
          <span className="text-sm text-muted" style={{ marginLeft: 12 }}>Click to show QR</span>
        </div>
      )}

      {remoteUrl && !status?.startsWith('running') === false && (
        <RemoteControlModal url={remoteUrl} onClose={() => {}} />
      )}

      <LiveOutput events={events} status={status} />

      {report && (
        <div className="section" style={{ marginTop: 24 }}>
          <div className="section-title">Agent Report</div>
          <ReportView report={report} />
        </div>
      )}
    </div>
  );
}
