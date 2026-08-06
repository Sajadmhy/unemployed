import { cn } from "@/lib/utils";

/** A grey block standing in for content that is on its way.
 *
 * Shaped like the thing it replaces, so the page does not jump when the data
 * lands — which is the only reason to prefer this over the word "Loading…".
 */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("animate-pulse rounded bg-muted", className)}
    />
  );
}

/** Placeholder rows for the bordered lists used across the app. */
export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="rounded-lg border divide-y" role="status" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-3 px-4 py-4">
          <Skeleton className="size-5 shrink-0 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5 w-1/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}
