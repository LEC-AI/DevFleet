import React from 'react';

const trendArrows = {
  up: 'M7 14l5-5 5 5',
  down: 'M7 10l5 5 5-5',
  neutral: 'M4 12h16',
};

const trendColors = {
  up: 'var(--success)',
  down: 'var(--danger)',
  neutral: 'var(--text-muted)',
};

export default function StatsCard({ label, value, accent = false, icon, trend, color }) {
  const accentLine = color || (accent ? 'var(--accent)' : null);

  return (
    <div
      className={`stats-card ${accent ? 'stats-card--accent' : ''}`}
      style={{
        position: 'relative',
        overflow: 'hidden',
        borderTop: accentLine ? `3px solid ${accentLine}` : undefined,
      }}
    >
      {/* Subtle glow behind the card when accented */}
      {accentLine && (
        <div
          style={{
            position: 'absolute',
            top: -30,
            right: -30,
            width: 80,
            height: 80,
            borderRadius: '50%',
            background: accentLine,
            opacity: 0.06,
            filter: 'blur(20px)',
            pointerEvents: 'none',
          }}
        />
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="stats-label">{label}</span>
        {icon && (
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke={accentLine || 'var(--text-dim)'}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ opacity: 0.7, flexShrink: 0 }}
          >
            <path d={icon} />
          </svg>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10 }}>
        <span className="stats-value stats-value--animated">{value}</span>
        {trend && (
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke={trendColors[trend] || trendColors.neutral}
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ marginBottom: 6 }}
          >
            <path d={trendArrows[trend] || trendArrows.neutral} />
          </svg>
        )}
      </div>
    </div>
  );
}
