type FeedbackProps = {
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void; disabled?: boolean };
};

export function LoadingState({ label }: { label: string }) {
  return (
    <section className="shared-state shared-state-loading" role="status" aria-busy="true" aria-live="polite">
      <span aria-hidden="true">✳</span>
      <p>{label}</p>
    </section>
  );
}

export function ErrorState({ title, description, action }: FeedbackProps) {
  return (
    <section className="shared-state shared-state-error" role="alert" aria-live="assertive">
      <span aria-hidden="true">!</span>
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {action && (
        <button type="button" onClick={action.onClick} disabled={action.disabled}>
          {action.label}
        </button>
      )}
    </section>
  );
}

export function EmptyState({ title, description }: Omit<FeedbackProps, "action">) {
  return (
    <section className="shared-state shared-state-empty" role="status">
      <span aria-hidden="true">✳</span>
      <h2>{title}</h2>
      {description && <p>{description}</p>}
    </section>
  );
}
