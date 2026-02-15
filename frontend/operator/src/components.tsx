import React from "react";

export function CodeBlock({ value }: { value: unknown }) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return (
    <pre className="code">
      <code>{text}</code>
    </pre>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="spinner">
      <div className="dot" />
      <div className="dot" />
      <div className="dot" />
      {label ? <span className="spinnerLabel">{label}</span> : null}
    </div>
  );
}

export function ErrorBox({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="error">
      <div className="errorTitle">Error</div>
      <div className="errorMsg">{msg}</div>
    </div>
  );
}

