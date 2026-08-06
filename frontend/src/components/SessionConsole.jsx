import React, { useState, useEffect, useRef } from 'react';
import { streamSession } from '../api/client';

/**
 * Tails live output from one or more agent sessions.
 *
 * On the master dashboard it is passed every active session, so it reads as one
 * feed of everything the fleet is doing. On a member's tab it gets only their
 * sessions, so it shows only their own environment.
 */
const MAX_LINES = 400;   // ring buffer: an overnight run would otherwise grow without bound

export default function SessionConsole({ sessions = [], title = 'Console', navigate }) {
  const [lines, setLines] = useState([]);
  const [paused, setPaused] = useState(false);
  const bodyRef = useRef(null);
  const pausedRef = useRef(false);
  pausedRef.current = paused;

  const ids = sessions.map(s => s.session_id || s.id).filter(Boolean).join(',');

  useEffect(() => {
    if (!ids) { setLines([]); return; }
    const closers = [];

    for (const s of sessions) {
      const sid = s.session_id || s.id;
      if (!sid) continue;
      const label = (s.title || s.mission_title || sid.slice(0, 8));
      const push = (text, kind) => {
        if (pausedRef.current || !text) return;
        setLines(prev => {
          const next = [...prev, { sid, label, kind, text: String(text).replace(/\n$/, '') }];
          return next.length > MAX_LINES ? next.slice(-MAX_LINES) : next;
        });
      };
      try {
        const close = streamSession(sid, {
          onBackfill: evs => (evs || []).slice(-40).forEach(e => push(e.text, e.type)),
          onEvent: e => push(e.text, e.type),
          onDone: d => push(`— session ${d?.status || 'ended'} —`, 'done'),
          onError: () => push('— stream lost —', 'error'),
        });
        if (typeof close === 'function') closers.push(close);
      } catch {
        /* a dead session shouldn't take the console down */
      }
    }
    return () => closers.forEach(c => { try { c(); } catch {} });
  }, [ids]);

  useEffect(() => {
    if (!paused && bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [lines, paused]);

  return (
    <div className="console">
      <div className="console-head">
        <span className="console-title">
          {title}
          <span className="text-dim">
            {' '}· {sessions.length} session{sessions.length !== 1 ? 's' : ''}
          </span>
        </span>
        <div className="flex gap-8">
          <button className="btn btn-sm" onClick={() => setPaused(p => !p)}>
            {paused ? 'Resume' : 'Pause'}
          </button>
          <button className="btn btn-sm" onClick={() => setLines([])}>Clear</button>
        </div>
      </div>
      <div className="console-body" ref={bodyRef}>
        {lines.length === 0 ? (
          <div className="console-line console-line--dim">
            {sessions.length === 0
              ? 'No active sessions. Output appears here when agents run.'
              : 'Waiting for output…'}
          </div>
        ) : lines.map((l, i) => (
          <div key={i} className={`console-line console-line--${l.kind || 'text'}`}>
            <span className="console-src"
                  onClick={() => navigate?.('live', l.sid)}
                  title="Open this session">{l.label}</span>
            <span className="console-text">{l.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
