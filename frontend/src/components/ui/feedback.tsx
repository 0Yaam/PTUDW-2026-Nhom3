type FeedbackProps = { title: string; description?: string; action?: { label: string; onClick: () => void } };

export function LoadingState({ label }: { label: string }) {
  return <section className="shared-state shared-state-loading" aria-busy="true" aria-live="polite"><span aria-hidden="true">✳</span><p>{label}</p></section>;
}

export function ErrorState({ title, description, action }: FeedbackProps) {
  return <section className="shared-state shared-state-error" role="alert"><span aria-hidden="true">!</span><h2>{title}</h2>{description && <p>{description}</p>}{action && <button type="button" onClick={action.onClick}>{action.label}</button>}</section>;
}

export function EmptyState({ title, description }: Omit<FeedbackProps, "action">) {
  return <section className="shared-state shared-state-empty"><span aria-hidden="true">✳</span><h2>{title}</h2>{description && <p>{description}</p>}</section>;
}
