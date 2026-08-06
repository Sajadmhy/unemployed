"use client";

import { useEffect, useState } from "react";

import { GoBackTo } from "@/components/go-back-to";

/**
 * "Something is happening and it is not stuck."
 *
 * The local model takes 30–40 seconds per call and reports no progress, so
 * there is nothing honest to put in a percentage. An elapsed counter is honest:
 * it proves the app is alive and lets you judge whether this run is unusual.
 */
export function Working({ label }: { label: string }) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="space-y-1.5" role="status" aria-live="polite">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span className="tabular-nums">{seconds}s</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded bg-muted">
        <div className="h-full w-1/3 animate-pulse rounded bg-foreground/70" />
      </div>
      <GoBackTo />
    </div>
  );
}
