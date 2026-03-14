import React from 'react';

export default function PromptEditor({ value, onChange, readOnly = false, placeholder }) {
  return (
    <textarea
      className="prompt-editor"
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
      readOnly={readOnly}
      placeholder={placeholder || 'Write a detailed implementation prompt for the coding agent...'}
      spellCheck={false}
    />
  );
}
