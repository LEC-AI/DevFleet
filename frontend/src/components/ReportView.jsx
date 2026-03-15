import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const SECTIONS = [
  { key: 'errors_encountered', label: 'Human Input Needed', variant: 'errors', icon: '🚨' },
  { key: 'what_done', label: "What's Done", variant: 'done', icon: '✅' },
  { key: 'what_open', label: "What's Open", variant: 'open', icon: '🔲' },
  { key: 'what_tested', label: "What's Tested", variant: 'tested', icon: '🧪' },
  { key: 'what_untested', label: "What's Not Tested", variant: 'untested', icon: '⚠️' },
  { key: 'next_steps', label: 'Recommended Next Missions', variant: 'next', icon: '🎯' },
  { key: 'files_changed', label: 'Files Changed', variant: 'files', icon: '📁' },
];

export default function ReportView({ report }) {
  if (!report) return null;

  return (
    <div>
      {SECTIONS.map(({ key, label, variant, icon }) => {
        const content = report[key];
        if (!content || content.trim() === '' || content.trim().toLowerCase() === 'none') return null;
        return (
          <div key={key} className={`report-section report-section--${variant}`}>
            <div className="report-section-header">{icon} {label}</div>
            <div className="report-section-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          </div>
        );
      })}
    </div>
  );
}
