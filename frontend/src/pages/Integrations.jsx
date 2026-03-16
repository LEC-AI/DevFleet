import React, { useState } from 'react';

const INTEGRATIONS = [
  {
    id: 'claude-code',
    name: 'Claude Code',
    description: 'Use DevFleet directly from the Claude Code CLI or as a slash command. Plan projects, dispatch agents, and read reports — all from your terminal.',
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="4 17 10 11 4 5" /><line x1="12" y1="19" x2="20" y2="19" />
      </svg>
    ),
    transport: 'Streamable HTTP',
    setupMethods: [
      {
        label: 'CLI (recommended)',
        command: 'claude mcp add devfleet --transport http http://localhost:18801/mcp',
      },
      {
        label: 'Project config (.claude/settings.json)',
        code: `{
  "mcpServers": {
    "devfleet": {
      "type": "http",
      "url": "http://localhost:18801/mcp"
    }
  }
}`,
      },
    ],
    skillSetup: {
      description: 'Install the DevFleet slash command for quick access:',
      command: 'mkdir -p .claude/commands && cp integrations/ecc/devfleet.md .claude/commands/devfleet.md',
      usage: '/devfleet Build a REST API with auth and tests',
    },
    docsUrl: 'https://github.com/LEC-AI/claude-devfleet/tree/main/integrations/ecc',
    features: ['Slash command support', 'Skill system integration', 'Full MCP tool access', 'Auto-dispatch chains'],
  },
  {
    id: 'openclaw',
    name: 'OpenClaw / NanoClaw',
    description: 'Trigger DevFleet from the NanoClaw REPL. Load the DevFleet skill, describe what to build, and NanoClaw orchestrates the full plan-dispatch-report cycle.',
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2a5 5 0 015 5v1a5 5 0 01-10 0V7a5 5 0 015-5z" /><path d="M8 14s1.5 2 4 2 4-2 4-2" /><path d="M9 9h.01" /><path d="M15 9h.01" /><path d="M12 13v3" /><path d="M7 16.5S4 18 4 20h16c0-2-3-3.5-3-3.5" />
      </svg>
    ),
    transport: 'Streamable HTTP',
    setupMethods: [
      {
        label: 'Register MCP server',
        command: 'claude mcp add devfleet --transport http http://localhost:18801/mcp',
      },
      {
        label: 'Install skill',
        command: 'cp integrations/openclaw/devfleet-skill.md /path/to/ecc/skills/claude-devfleet/SKILL.md',
      },
    ],
    skillSetup: {
      description: 'Launch with the skill pre-loaded:',
      command: 'CLAW_SKILLS=claude-devfleet node scripts/claw.js',
      usage: 'Use DevFleet to build a Python CLI tool that converts CSV to JSON.',
    },
    docsUrl: 'https://github.com/LEC-AI/claude-devfleet/tree/main/integrations/openclaw',
    features: ['REPL-driven workflow', 'Skill auto-loading', 'Plan approval loop', 'Auto-dispatch chains'],
  },
  {
    id: 'cursor',
    name: 'Cursor',
    description: 'Add DevFleet as an MCP server in Cursor. Dispatch coding agents, plan projects, and read mission reports through Cursor\'s AI chat.',
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
      </svg>
    ),
    transport: 'Streamable HTTP',
    setupMethods: [
      {
        label: 'Cursor Settings',
        steps: ['Open Settings (Cmd+,)', 'Navigate to Features > MCP Servers', 'Click Add new MCP server'],
      },
      {
        label: 'Project config (.cursor/mcp.json)',
        code: `{
  "mcpServers": {
    "devfleet": {
      "type": "http",
      "url": "http://localhost:18801/mcp"
    }
  }
}`,
      },
    ],
    docsUrl: 'https://github.com/LEC-AI/claude-devfleet/tree/main/integrations/cursor',
    features: ['Native MCP support', 'AI chat integration', 'Project & global config', 'All 11 tools available'],
  },
  {
    id: 'windsurf',
    name: 'Windsurf',
    description: 'Connect Windsurf (Codeium) to DevFleet via MCP. Use Cascade to plan and dispatch multi-agent coding tasks from your editor.',
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17.7 7.7a7.5 7.5 0 10-10.6 10.6" /><path d="M21 12h-2" /><path d="M12 3v2" /><path d="M4.2 4.2l1.4 1.4" /><circle cx="12" cy="12" r="3" />
      </svg>
    ),
    transport: 'Streamable HTTP',
    setupMethods: [
      {
        label: 'Windsurf MCP config (~/.codeium/windsurf/mcp_config.json)',
        code: `{
  "mcpServers": {
    "devfleet": {
      "serverUrl": "http://localhost:18801/mcp"
    }
  }
}`,
      },
    ],
    docsUrl: 'https://github.com/LEC-AI/claude-devfleet',
    features: ['Cascade AI integration', 'MCP tool access', 'Project orchestration'],
  },
  {
    id: 'custom-mcp',
    name: 'Any MCP Client',
    description: 'DevFleet exposes a standard MCP server via Streamable HTTP. Any MCP-compatible client can connect and use all 11 orchestration tools.',
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
      </svg>
    ),
    transport: 'Streamable HTTP + SSE (legacy)',
    setupMethods: [
      {
        label: 'Streamable HTTP (recommended)',
        code: `Endpoint: http://localhost:18801/mcp
Methods: GET, POST, DELETE
Header: mcp-session-id (auto-assigned)`,
      },
      {
        label: 'SSE (legacy, deprecated)',
        code: `SSE endpoint: http://localhost:18801/mcp/sse
POST messages: http://localhost:18801/mcp/messages/`,
      },
    ],
    docsUrl: 'https://github.com/LEC-AI/claude-devfleet',
    features: ['11 orchestration tools', 'Streamable HTTP transport', 'SSE backward compat', 'JSON-RPC 2.0'],
  },
];

const MCP_TOOLS = [
  { name: 'plan_project', args: 'prompt', desc: 'AI breaks description into chained missions with dependency DAG' },
  { name: 'create_project', args: 'name, path?, description?', desc: 'Create a project manually' },
  { name: 'create_mission', args: 'project_id, title, prompt, depends_on?, auto_dispatch?', desc: 'Add a mission with dependencies' },
  { name: 'dispatch_mission', args: 'mission_id, model?, max_turns?', desc: 'Start an agent on a mission' },
  { name: 'cancel_mission', args: 'mission_id', desc: 'Stop a running agent' },
  { name: 'wait_for_mission', args: 'mission_id, timeout_seconds?', desc: 'Block until mission completes (max 1800s)' },
  { name: 'get_mission_status', args: 'mission_id', desc: 'Check mission progress without blocking' },
  { name: 'get_report', args: 'mission_id', desc: 'Structured report: files_changed, what_done, errors, next_steps' },
  { name: 'get_dashboard', args: '', desc: 'System overview: running agents, slots, recent activity' },
  { name: 'list_projects', args: '', desc: 'Browse all projects' },
  { name: 'list_missions', args: 'project_id, status?', desc: 'List missions in a project' },
];

export default function Integrations({ navigate }) {
  const [expandedId, setExpandedId] = useState(null);
  const [copiedCmd, setCopiedCmd] = useState(null);

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(id);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h2>Integrations</h2>
          <p>Connect DevFleet to your favorite editor or agent framework via MCP</p>
        </div>
      </div>

      {/* Flow Diagram */}
      <div style={{
        padding: '20px 24px',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg, 12px)',
        marginBottom: 24,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-text)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" />
          </svg>
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--accent-text)' }}>
            How It Works
          </span>
        </div>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0,
          padding: '12px 0', overflowX: 'auto',
        }}>
          {[
            { label: 'Your Editor / REPL', sub: 'Claude Code, Cursor, etc.', color: 'var(--accent)' },
            { label: 'MCP Protocol', sub: 'Streamable HTTP', color: 'var(--text-dim)', isArrow: true },
            { label: 'DevFleet API', sub: ':18801/mcp', color: 'var(--success)' },
            { label: 'Mission DAG', sub: 'Plan + Dependencies', color: 'var(--text-dim)', isArrow: true },
            { label: 'Agent Worktrees', sub: 'Isolated git branches', color: 'var(--warning)' },
          ].map((step, i) =>
            step.isArrow ? (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '0 6px', flexShrink: 0 }}>
                <svg width="32" height="16" viewBox="0 0 32 16" fill="none" stroke="var(--text-dim)" strokeWidth="1.5">
                  <line x1="0" y1="8" x2="26" y2="8" /><polyline points="22,3 28,8 22,13" />
                </svg>
                <span style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 2, whiteSpace: 'nowrap' }}>{step.sub}</span>
              </div>
            ) : (
              <div key={i} style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                padding: '10px 16px', minWidth: 120, flexShrink: 0,
                background: 'var(--bg-base)', borderRadius: 'var(--radius-md)',
                border: `1px solid ${step.color}22`,
              }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{step.label}</span>
                <span style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, whiteSpace: 'nowrap' }}>{step.sub}</span>
              </div>
            )
          )}
        </div>
      </div>

      {/* Integration Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
        gap: 16,
        marginBottom: 32,
      }}>
        {INTEGRATIONS.map(integration => {
          const isExpanded = expandedId === integration.id;
          return (
            <div
              key={integration.id}
              style={{
                padding: '20px 22px',
                background: 'var(--bg-surface)',
                border: `1px solid ${isExpanded ? 'var(--accent)' : 'var(--border)'}`,
                borderRadius: 'var(--radius-lg, 12px)',
                transition: 'border-color 0.2s, box-shadow 0.2s',
                cursor: 'pointer',
                ...(isExpanded ? { boxShadow: '0 0 0 1px var(--accent)' } : {}),
              }}
              onClick={() => setExpandedId(isExpanded ? null : integration.id)}
            >
              {/* Card Header */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 12 }}>
                <div style={{
                  color: 'var(--accent-text)', flexShrink: 0,
                  width: 40, height: 40, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: 'rgba(218,119,86,0.08)', borderRadius: 'var(--radius-md)',
                }}>
                  {integration.icon}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                      {integration.name}
                    </h3>
                    <span style={{
                      fontSize: 9, padding: '2px 8px',
                      background: 'rgba(34,197,94,0.08)', color: 'var(--success)',
                      borderRadius: 'var(--radius-full)', fontWeight: 600,
                      textTransform: 'uppercase', letterSpacing: '0.05em',
                    }}>
                      {integration.transport}
                    </span>
                  </div>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '6px 0 0', lineHeight: 1.5 }}>
                    {integration.description}
                  </p>
                </div>
              </div>

              {/* Feature Tags */}
              {integration.features && (
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: isExpanded ? 16 : 0 }}>
                  {integration.features.map(f => (
                    <span key={f} style={{
                      fontSize: 10, padding: '3px 8px',
                      background: 'var(--bg-base)', color: 'var(--text-secondary)',
                      borderRadius: 'var(--radius-full)', fontWeight: 500,
                    }}>{f}</span>
                  ))}
                </div>
              )}

              {/* Expanded Setup Details */}
              {isExpanded && (
                <div onClick={e => e.stopPropagation()} style={{ marginTop: 4 }}>
                  <div style={{
                    borderTop: '1px solid var(--border)', paddingTop: 16,
                  }}>
                    <span style={{
                      fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
                      letterSpacing: '0.08em', color: 'var(--text-secondary)',
                    }}>
                      Setup
                    </span>

                    {integration.setupMethods.map((method, i) => (
                      <div key={i} style={{ marginTop: 12 }}>
                        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>
                          {method.label}
                        </span>
                        {method.command && (
                          <div style={{
                            display: 'flex', alignItems: 'center', gap: 8, marginTop: 6,
                            padding: '8px 12px', background: 'var(--bg-base)',
                            borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)', fontSize: 11,
                          }}>
                            <code style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }}>
                              {method.command}
                            </code>
                            <button
                              onClick={() => copyToClipboard(method.command, `${integration.id}-${i}`)}
                              style={{
                                background: 'none', border: 'none', cursor: 'pointer',
                                color: copiedCmd === `${integration.id}-${i}` ? 'var(--success)' : 'var(--text-dim)',
                                fontSize: 10, fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0,
                              }}
                            >
                              {copiedCmd === `${integration.id}-${i}` ? 'Copied!' : 'Copy'}
                            </button>
                          </div>
                        )}
                        {method.code && (
                          <pre style={{
                            marginTop: 6, padding: '10px 14px',
                            background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)',
                            fontFamily: 'var(--font-mono)', fontSize: 11,
                            color: 'var(--text-secondary)', lineHeight: 1.5,
                            overflow: 'auto', maxHeight: 160,
                          }}>
                            {method.code}
                          </pre>
                        )}
                        {method.steps && (
                          <ol style={{
                            marginTop: 6, paddingLeft: 20,
                            fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.8,
                          }}>
                            {method.steps.map((s, j) => <li key={j}>{s}</li>)}
                          </ol>
                        )}
                      </div>
                    ))}

                    {integration.skillSetup && (
                      <div style={{ marginTop: 16 }}>
                        <span style={{
                          fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
                          letterSpacing: '0.08em', color: 'var(--text-secondary)',
                        }}>
                          Skill / Command
                        </span>
                        <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '6px 0' }}>
                          {integration.skillSetup.description}
                        </p>
                        <div style={{
                          display: 'flex', alignItems: 'center', gap: 8,
                          padding: '8px 12px', background: 'var(--bg-base)',
                          borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)', fontSize: 11,
                        }}>
                          <code style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }}>
                            {integration.skillSetup.command}
                          </code>
                          <button
                            onClick={() => copyToClipboard(integration.skillSetup.command, `${integration.id}-skill`)}
                            style={{
                              background: 'none', border: 'none', cursor: 'pointer',
                              color: copiedCmd === `${integration.id}-skill` ? 'var(--success)' : 'var(--text-dim)',
                              fontSize: 10, fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0,
                            }}
                          >
                            {copiedCmd === `${integration.id}-skill` ? 'Copied!' : 'Copy'}
                          </button>
                        </div>
                        <div style={{
                          marginTop: 8, padding: '8px 12px', background: 'rgba(218,119,86,0.04)',
                          borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--accent)',
                        }}>
                          <span style={{ fontSize: 10, color: 'var(--text-dim)', fontWeight: 600 }}>Example:</span>
                          <code style={{
                            display: 'block', marginTop: 2, fontSize: 11,
                            fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)',
                          }}>
                            {integration.skillSetup.usage}
                          </code>
                        </div>
                      </div>
                    )}

                    {/* Docs Link */}
                    <div style={{ marginTop: 14 }}>
                      <a
                        href={integration.docsUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          fontSize: 11, fontWeight: 600, color: 'var(--accent-text)',
                          textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4,
                        }}
                      >
                        View full documentation
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
                        </svg>
                      </a>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* MCP Tools Reference */}
      <div style={{
        padding: '20px 24px',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg, 12px)',
        marginBottom: 24,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent-text)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" />
          </svg>
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
            Available MCP Tools
          </span>
          <span style={{
            fontSize: 10, padding: '2px 8px', marginLeft: 'auto',
            background: 'rgba(218,119,86,0.08)', color: 'var(--accent-text)',
            borderRadius: 'var(--radius-full)', fontWeight: 600,
          }}>
            {MCP_TOOLS.length} tools
          </span>
        </div>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14, lineHeight: 1.5 }}>
          These tools are available to any MCP client connected to DevFleet at <code style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>http://localhost:18801/mcp</code>
        </p>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600, fontSize: 11 }}>Tool</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600, fontSize: 11 }}>Parameters</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600, fontSize: 11 }}>Description</th>
              </tr>
            </thead>
            <tbody>
              {MCP_TOOLS.map(tool => (
                <tr key={tool.name} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent-text)', fontWeight: 600, whiteSpace: 'nowrap' }}>
                    {tool.name}
                  </td>
                  <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)' }}>
                    {tool.args || '—'}
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>
                    {tool.desc}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Connection Info */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 16,
        marginBottom: 24,
      }}>
        {/* Quick Connect */}
        <div style={{
          padding: '18px 22px',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg, 12px)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-secondary)' }}>
              Quick Connect
            </span>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10, lineHeight: 1.5 }}>
            Fastest way to get started — works with Claude Code, NanoClaw, and any CLI-registered MCP client:
          </p>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 14px', background: 'var(--bg-base)',
            borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)', fontSize: 12,
          }}>
            <code style={{ flex: 1, color: 'var(--text-secondary)' }}>
              claude mcp add devfleet --transport http http://localhost:18801/mcp
            </code>
            <button
              onClick={() => copyToClipboard('claude mcp add devfleet --transport http http://localhost:18801/mcp', 'quick')}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: copiedCmd === 'quick' ? 'var(--success)' : 'var(--text-dim)',
                fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap',
              }}
            >
              {copiedCmd === 'quick' ? 'Copied!' : 'Copy'}
            </button>
          </div>
        </div>

        {/* Transport Info */}
        <div style={{
          padding: '18px 22px',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg, 12px)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-text)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
            </svg>
            <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-secondary)' }}>
              Transport Endpoints
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
              background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)',
            }}>
              <span style={{
                fontSize: 9, padding: '2px 8px',
                background: 'rgba(34,197,94,0.1)', color: 'var(--success)',
                borderRadius: 'var(--radius-full)', fontWeight: 700,
              }}>RECOMMENDED</span>
              <code style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)' }}>
                GET|POST|DELETE /mcp
              </code>
              <span style={{ fontSize: 10, color: 'var(--text-dim)', marginLeft: 'auto' }}>Streamable HTTP</span>
            </div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
              background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)',
            }}>
              <span style={{
                fontSize: 9, padding: '2px 8px',
                background: 'rgba(255,186,8,0.1)', color: 'var(--warning)',
                borderRadius: 'var(--radius-full)', fontWeight: 700,
              }}>LEGACY</span>
              <code style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)' }}>
                GET /mcp/sse + POST /mcp/messages/
              </code>
              <span style={{ fontSize: 10, color: 'var(--text-dim)', marginLeft: 'auto' }}>SSE (deprecated)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
