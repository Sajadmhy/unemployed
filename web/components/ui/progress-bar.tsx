/**
 * A determinate bar for work that reports real progress.
 *
 * `total = 0` renders the indeterminate pulse instead of a lying 0% — a step
 * that has not yet counted its work is not a step that has done none of it.
 */
export function ProgressBar({
  done,
  total,
  message,
}: {
  done: number;
  total: number;
  message: string;
}) {
  const pct = total > 0 ? Math.min(100, (done / total) * 100) : null;

  return (
    <div className="space-y-1.5" role="status" aria-live="polite">
      <div className="flex justify-between gap-4 text-xs text-muted-foreground">
        <span className="truncate">{message}</span>
        {total > 0 && (
          <span className="tabular-nums shrink-0">
            {done}/{total}
          </span>
        )}
      </div>
      <div className="h-1.5 overflow-hidden rounded bg-muted">
        <div
          className={`h-full rounded bg-foreground/70 transition-all ${
            pct === null ? "w-1/3 animate-pulse" : ""
          }`}
          style={pct === null ? undefined : { width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
