"use client";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="error-shell">
      <p className="eyebrow">Connection problem</p>
      <h1>The kitchen is not ready.</h1>
      <p>Check FastAPI and PostgreSQL, then try again.</p>
      <button type="button" onClick={reset}>Try again</button>
    </main>
  );
}
