import React, { useState } from 'react';
import { setMemberCredentials, verifyMember } from '../api/client';

/**
 * Shown instead of a member's dashboard until their environment is proven.
 * "Proven" means the tokens were actually used against GitHub and Claude — not
 * that they look plausible. Until both pass, no dashboard and no dispatch.
 */
export default function EnvironmentSetup({ memberId, name, readiness, onReady }) {
  const [github, setGithub] = useState('');
  const [claude, setClaude] = useState('');
  const [linuxUser, setLinuxUser] = useState(readiness?.linux_user || '');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState('');

  const submit = async () => {
    if (!github && !claude) { setErr('Enter at least one token'); return; }
    setBusy(true); setErr(''); setResult(null);
    try {
      const r = await setMemberCredentials(memberId, {
        github_token: github || null,
        claude_token: claude || null,
        linux_user: linuxUser || null,
      });
      setResult(r);
      setGithub(''); setClaude('');       // don't leave secrets sitting in the DOM
      if (r.ready) onReady?.();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  const recheck = async () => {
    setBusy(true); setErr('');
    try {
      const r = await verifyMember(memberId);
      setResult(r);
      if (r.ready) onReady?.();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  const state = result || readiness;
  const checks = result?.checks;
  const row = (label, ok, detail) => (
    <div className="list-row">
      <div>
        <strong>{label}</strong>
        {detail && <div className="text-dim">{detail}</div>}
      </div>
      <span className={`status-badge status-badge--${ok ? 'completed' : 'draft'}`}>
        {ok ? 'verified' : 'not verified'}
      </span>
    </div>
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>{name}</h2>
          <p>Environment not ready — dashboard locked</p>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">Environment checks</h3>
        {row('GitHub', state?.github?.verified,
             checks?.github?.error ||
             (state?.github?.login ? `authenticated as ${state.github.login}` :
              state?.github?.stored ? 'token stored, not yet verified' : 'no token yet'))}
        {row('Claude', state?.claude?.verified,
             checks?.claude?.error ||
             (state?.claude?.verified ? 'completed a live test call' :
              state?.claude?.stored ? 'token stored, not yet verified' : 'no token yet'))}
        {row('Workspace', state?.workspace?.exists,
             state?.workspace?.path
               ? `${state.workspace.path} — agents work here and may not write outside it`
               : '')}
      </div>

      <div className="card">
        <h3 className="card-title">Connect {name}&rsquo;s environment</h3>
        <p className="text-dim" style={{ marginBottom: 12 }}>
          Tokens are written to a private file with <code>0600</code> permissions, never
          to the database. Both are tested against the real services before this
          unlocks — verifying Claude makes one small billed call.
        </p>

        <label className="form-label">GitHub token</label>
        <input
          className="form-input" type="password" autoComplete="off"
          placeholder="ghp_… or github_pat_… (needs repo scope)"
          value={github} onChange={e => setGithub(e.target.value)}
        />
        <p className="text-dim" style={{ marginTop: -4, marginBottom: 12 }}>
          A personal access token, not a password — it can be scoped and revoked.
        </p>

        <label className="form-label">Claude OAuth token</label>
        <input
          className="form-input" type="password" autoComplete="off"
          placeholder="sk-ant-oat01-… (from `claude setup-token`)"
          value={claude} onChange={e => setClaude(e.target.value)}
        />

        <label className="form-label">Linux user (optional)</label>
        <input
          className="form-input" placeholder="e.g. kaif — the account agents run as"
          value={linuxUser} onChange={e => setLinuxUser(e.target.value)}
        />

        {err && <div className="error-banner" style={{ marginTop: 12 }}>{err}</div>}

        <div className="form-row" style={{ marginTop: 12 }}>
          <button className="btn btn-primary" disabled={busy} onClick={submit}>
            {busy ? 'Verifying…' : 'Save & verify'}
          </button>
          <button className="btn" disabled={busy} onClick={recheck}>Re-check</button>
        </div>

        {state?.missing?.length > 0 && (
          <p className="text-dim" style={{ marginTop: 12 }}>
            Outstanding: {state.missing.join(' · ')}
          </p>
        )}
      </div>

      <p className="text-dim">
        Note: this gate stops half-configured environments from dispatching agents.
        It is not authentication — the API has no login yet, so anyone who can reach
        it can act as anyone.
      </p>
    </div>
  );
}
