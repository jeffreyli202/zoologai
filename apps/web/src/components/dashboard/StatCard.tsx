type StatCardProps = {
  label: string;
  value: number | string;
  hint?: string;
  isMock?: boolean;
};

export function StatCard({ label, value, hint, isMock = false }: StatCardProps) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-muted">{label}</p>
        {isMock ? (
          <span className="rounded-md bg-sage-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-sage-700">
            Mock
          </span>
        ) : null}
      </div>
      <p className="mt-3 font-display text-3xl text-sage-900">{value}</p>
      {hint ? <p className="mt-2 text-xs leading-5 text-muted">{hint}</p> : null}
    </div>
  );
}
