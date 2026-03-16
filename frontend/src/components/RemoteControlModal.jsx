import React, { useState, useEffect, useRef } from 'react';

/**
 * QR Code generator using QR Server API.
 */
function QRCode({ url, size = 180 }) {
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encodeURIComponent(url)}&bgcolor=0a0a0a&color=22c55e&format=svg`;

  return (
    <div style={qrStyles.wrapper}>
      {/* Pulsing glow border */}
      <div style={qrStyles.glowRing}>
        {/* Phone mockup frame */}
        <div style={qrStyles.phoneMockup}>
          {/* Phone notch */}
          <div style={qrStyles.phoneNotch} />
          {/* QR image */}
          <img
            src={qrUrl}
            alt="QR Code"
            width={size}
            height={size}
            style={{ borderRadius: 4, background: '#0a0a0a', display: 'block' }}
          />
          {/* Phone home bar */}
          <div style={qrStyles.phoneHomeBar} />
        </div>
      </div>
    </div>
  );
}

const qrStyles = {
  wrapper: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 8,
  },
  glowRing: {
    padding: 3,
    borderRadius: 24,
    background: 'linear-gradient(135deg, rgba(34,197,94,0.4), rgba(218,119,86,0.4), rgba(34,197,94,0.4))',
    backgroundSize: '300% 300%',
    animation: 'rcm-glowPulse 3s ease-in-out infinite, rcm-glowRotate 6s linear infinite',
    boxShadow: '0 0 30px rgba(34,197,94,0.15), 0 0 60px rgba(218,119,86,0.08)',
  },
  phoneMockup: {
    background: '#111114',
    borderRadius: 22,
    padding: '14px 10px 10px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 6,
    border: '2px solid rgba(255,255,255,0.08)',
    position: 'relative',
  },
  phoneNotch: {
    width: 60,
    height: 6,
    borderRadius: 3,
    background: 'rgba(255,255,255,0.1)',
    marginBottom: 4,
  },
  phoneHomeBar: {
    width: 40,
    height: 4,
    borderRadius: 2,
    background: 'rgba(255,255,255,0.08)',
    marginTop: 2,
  },
};

/* Inject keyframes once */
const _injectStyles = typeof document !== 'undefined' && (() => {
  const id = 'rcm-keyframes';
  if (!document.getElementById(id)) {
    const s = document.createElement('style');
    s.id = id;
    s.textContent = `
      @keyframes rcm-glowPulse {
        0%, 100% { box-shadow: 0 0 30px rgba(34,197,94,0.15), 0 0 60px rgba(218,119,86,0.08); }
        50%      { box-shadow: 0 0 40px rgba(34,197,94,0.3), 0 0 80px rgba(218,119,86,0.15); }
      }
      @keyframes rcm-glowRotate {
        0%   { background-position: 0% 50%; }
        50%  { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
      }
      @keyframes rcm-livePulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50%      { opacity: 0.5; transform: scale(0.85); }
      }
      @keyframes rcm-livePulseRing {
        0%   { transform: scale(1); opacity: 0.4; }
        100% { transform: scale(2.5); opacity: 0; }
      }
      .rcm-copy-btn:hover {
        background: var(--accent-hover) !important;
        box-shadow: 0 0 16px rgba(218,119,86,0.3);
      }
      .rcm-open-btn:hover {
        box-shadow: 0 6px 24px rgba(34,197,94,0.35) !important;
        transform: translateY(-1px);
      }
      .rcm-open-btn:active {
        transform: translateY(0);
      }
    `;
    document.head.appendChild(s);
  }
})();

const ms = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.7)',
    backdropFilter: 'blur(8px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
    animation: 'fadeIn 0.15s',
  },
  modal: {
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border-strong)',
    borderRadius: 'var(--radius-lg)',
    padding: '24px 24px 20px',
    width: '90%',
    maxWidth: 460,
    maxHeight: '90vh',
    overflowY: 'auto',
    animation: 'popIn 0.25s',
    textAlign: 'center',
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
  },
  closeBtn: {
    position: 'absolute',
    top: 10,
    right: 10,
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.1)',
    color: 'var(--text-secondary)',
    fontSize: 20,
    cursor: 'pointer',
    padding: '4px 10px',
    borderRadius: 'var(--radius-sm)',
    transition: 'all 0.15s',
    lineHeight: 1,
    zIndex: 10,
  },
  liveIndicator: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '5px 14px',
    background: 'rgba(34,197,94,0.08)',
    border: '1px solid rgba(34,197,94,0.2)',
    borderRadius: 'var(--radius-full)',
    fontSize: 12,
    fontWeight: 600,
    color: '#22c55e',
    marginBottom: 16,
  },
  liveDotWrapper: {
    position: 'relative',
    width: 10,
    height: 10,
  },
  liveDot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
    background: '#22c55e',
    animation: 'rcm-livePulse 2s ease-in-out infinite',
    position: 'absolute',
    top: 0,
    left: 0,
  },
  liveDotRing: {
    width: 10,
    height: 10,
    borderRadius: '50%',
    border: '2px solid #22c55e',
    position: 'absolute',
    top: 0,
    left: 0,
    animation: 'rcm-livePulseRing 2s ease-out infinite',
  },
  headerIcon: {
    display: 'flex',
    justifyContent: 'center',
    marginBottom: 10,
  },
  phoneIconSvg: {
    color: 'var(--accent)',
    filter: 'drop-shadow(0 0 12px rgba(218,119,86,0.3))',
  },
  title: {
    fontSize: 22,
    fontWeight: 700,
    marginBottom: 4,
    letterSpacing: '-0.02em',
  },
  subtitle: {
    fontSize: 13,
    color: 'var(--text-muted)',
    marginBottom: 20,
  },
  urlRow: {
    display: 'flex',
    gap: 0,
    width: '100%',
    marginTop: 20,
    borderRadius: 'var(--radius-sm)',
    overflow: 'hidden',
    border: '1px solid var(--border)',
  },
  urlInput: {
    flex: 1,
    background: 'var(--bg-input)',
    border: 'none',
    padding: '11px 14px',
    color: 'var(--text-primary)',
    fontSize: 12,
    fontFamily: 'var(--font-mono)',
    outline: 'none',
    textOverflow: 'ellipsis',
    minWidth: 0,
  },
  copyBtn: {
    background: 'var(--accent)',
    color: 'white',
    border: 'none',
    padding: '11px 18px',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s',
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    whiteSpace: 'nowrap',
  },
  stepsRow: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'center',
    gap: 0,
    width: '100%',
    marginTop: 16,
    position: 'relative',
  },
  stepItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 8,
    flex: 1,
    position: 'relative',
    zIndex: 1,
  },
  stepNumber: (active) => ({
    width: 32,
    height: 32,
    borderRadius: '50%',
    background: active ? 'var(--accent)' : 'var(--accent-soft)',
    color: active ? 'white' : 'var(--accent-text)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 14,
    fontWeight: 700,
    flexShrink: 0,
    boxShadow: active ? '0 0 16px rgba(218,119,86,0.3)' : 'none',
    transition: 'all 0.2s',
  }),
  stepText: {
    fontSize: 12,
    color: 'var(--text-secondary)',
    lineHeight: 1.4,
    textAlign: 'center',
    maxWidth: 130,
  },
  stepConnector: {
    position: 'absolute',
    top: 16,
    left: 'calc(50% + 20px)',
    width: 'calc(100% - 40px)',
    height: 2,
    background: 'linear-gradient(90deg, var(--accent) 0%, rgba(218,119,86,0.2) 100%)',
    zIndex: 0,
  },
  note: {
    fontSize: 11,
    color: 'var(--text-dim)',
    padding: '8px 14px',
    background: 'var(--bg-surface)',
    borderRadius: 'var(--radius-sm)',
    width: '100%',
    marginTop: 14,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    justifyContent: 'center',
  },
  actions: {
    display: 'flex',
    justifyContent: 'center',
    gap: 10,
    marginTop: 16,
    position: 'sticky',
    bottom: 0,
    paddingTop: 8,
    background: 'var(--bg-elevated)',
  },
  openBtn: {
    background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
    color: 'white',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    padding: '11px 28px',
    fontSize: 15,
    fontWeight: 700,
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    textDecoration: 'none',
    boxShadow: '0 4px 14px rgba(34,197,94,0.25)',
    letterSpacing: '-0.01em',
  },
  closeAction: {
    background: 'transparent',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
    padding: '11px 20px',
    fontSize: 14,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
};

const steps = [
  { num: '1', text: 'Scan QR or open link in browser' },
  { num: '2', text: 'Type "go" to start the mission' },
  { num: '3', text: 'Agent works with full mission context' },
];

export default function RemoteControlModal({ url, onClose }) {
  const [copied, setCopied] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    const handleEsc = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  const handleCopy = () => {
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div style={ms.overlay} onClick={onClose}>
      <div style={ms.modal} onClick={e => e.stopPropagation()}>
        {/* Close button */}
        <button style={ms.closeBtn} onClick={onClose}>{'\u00D7'}</button>

        {/* Live indicator */}
        <div style={ms.liveIndicator}>
          <div style={ms.liveDotWrapper}>
            <div style={ms.liveDot} />
            <div style={ms.liveDotRing} />
          </div>
          Session is live
        </div>

        {/* Header icon */}
        <div style={ms.headerIcon}>
          <svg style={ms.phoneIconSvg} width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
            <line x1="12" y1="18" x2="12.01" y2="18"/>
          </svg>
        </div>

        <h3 style={ms.title}>Remote Control</h3>
        <p style={ms.subtitle}>Scan from your phone to take over this agent session</p>

        {/* Hero QR */}
        <QRCode url={url} size={220} />

        {/* URL Copy Row */}
        <div style={ms.urlRow}>
          <input
            ref={inputRef}
            type="text"
            style={ms.urlInput}
            value={url}
            readOnly
            onClick={() => inputRef.current?.select()}
          />
          <button className="rcm-copy-btn" style={ms.copyBtn} onClick={handleCopy}>
            {copied ? (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                Copied!
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
                Copy
              </>
            )}
          </button>
        </div>

        {/* Steps — horizontal with connecting lines */}
        <div style={ms.stepsRow}>
          {steps.map((step, i) => (
            <div key={step.num} style={ms.stepItem}>
              <div style={ms.stepNumber(i === 0)}>{step.num}</div>
              <span style={ms.stepText}>{step.text}</span>
              {i < steps.length - 1 && <div style={ms.stepConnector} />}
            </div>
          ))}
        </div>

        {/* Hint */}
        <div style={{...ms.note, background: 'rgba(34,197,94,0.06)', border: '1px solid rgba(34,197,94,0.15)'}}>
          <span style={{ fontSize: 13 }}>💡</span>
          Type <strong style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>"go"</strong> or <strong style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>"start"</strong> — the mission context is pre-loaded.
        </div>

        {/* Actions */}
        <div style={ms.actions}>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="rcm-open-btn"
            style={ms.openBtn}
          >
            Open in Browser
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
              <polyline points="15 3 21 3 21 9"/>
              <line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
          </a>
          <button style={ms.closeAction} onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
