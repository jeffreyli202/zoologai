type StatePanelProps = {
  tone?: "neutral" | "danger";
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
};

/**
 * Props: values passed from a parent into this child component.
 * Here the parent decides the title/message; this component only displays them.
 */
export function StatePanel({
  tone = "neutral",
  title,
  message,
  actionLabel,
  onAction,
}: StatePanelProps) {
  const isDanger = tone === "danger";

  return (
    <div
      className={`rounded-2xl border px-5 py-6 ${
        isDanger
          ? "border-danger/30 bg-danger-soft"
          : "border-border bg-surface/80"
      }`}
      role="status"
    >
      <h3
        className={`font-display text-lg ${
          isDanger ? "text-danger" : "text-sage-900"
        }`}
      >
        {title}
      </h3>
      <p className="mt-2 text-sm leading-6 text-muted">{message}</p>
      {actionLabel && onAction ? (
        <button
          type="button"
          onClick={onAction}
          className="mt-4 rounded-lg bg-sage-700 px-3.5 py-2 text-sm font-medium text-cream transition hover:bg-sage-900"
        >
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
