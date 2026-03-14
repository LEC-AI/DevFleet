import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const SECTIONS = [
  { key: 'what_done', label: "What's Done", variant: 'done' },
  { key: 'what_open', label: "What's Open", variant: 'open' },
  { key: 'what_tested', label: "What's Tested", variant: 'tested' },
  { key: 'what_untested', label: "What's Not Tested", variant: 'untested' },
  { key: 'next_steps', label: 'Next Steps', variant: 'next' },
  { key: 'files_changed', label: 'Files Changed', variant: 'files' },
  { key: 'errors_encountered', label: 'Errors Encountered', variant: 'errors' },
];

export default function ReportView({ report }) {
  if (!report) return null;

  return (
    <div>
      {SECTIONS.map(({ key, label, variant }) => {
        const content = report[key];
        if (!content || content.trim() === '' || content.trim().toLowerCase() === 'none') return null;
        return (
          <div key={key} className={`report-section report-section--${variant}`}>
            <div className="report-section-header">{label}</div>
            <div className="report-section-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          </div>
        );
      })}
    </div>
  );
}
