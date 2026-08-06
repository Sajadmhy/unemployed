"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Match, type Status } from "@/lib/api";
import { scoreTone } from "@/lib/score";
import { useRemembered } from "@/lib/use-remembered";
import { FitBreakdown } from "@/components/matches/fit-breakdown";
import { StatusSelect } from "@/components/status-select";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { SkeletonRows } from "@/components/ui/skeleton";

/**
 * The daily loop, answering only four questions:
 *   What should I apply to today? Why is it a fit? Generate. Apply.
 *
 * This also absorbed the old /matches page: two nearly identical ranked lists
 * was a distinction only the developer understood. "Show filtered" reveals what
 * was excluded and why, without needing a second page.
 */
export default function TodayPage() {
  const [matches, setMatches] = useState<Match[]>([]);
  const [openId, setOpenId] = useState<number | null>(null);
  const [hideDone, setHideDone] = useRemembered("today.hideDone", true);
  const [showFiltered, setShowFiltered] = useRemembered("today.showFiltered", false);
  const [loading, setLoading] = useState(true);

  // The remembered toggle arrives one render after mount, so two requests can be
  // in flight at once. Without the guard the slower — and now wrong — answer wins.
  useEffect(() => {
    let current = true;
    setLoading(true);
    api
      .listMatches(50, showFiltered)
      .then((rows) => current && setMatches(rows))
      .catch(() => {}) // backend not reachable yet
      .finally(() => current && setLoading(false));
    return () => {
      current = false;
    };
  }, [showFiltered]);

  function setStatus(jobId: number, status: Status) {
    setMatches((prev) =>
      prev.map((m) => (m.job.id === jobId ? { ...m, status } : m)),
    );
  }

  const done = new Set<Status>(["applied", "closed"]);
  const visible = hideDone ? matches.filter((m) => !done.has(m.status)) : matches;
  const appliedCount = matches.filter((m) => m.status === "applied").length;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold">Apply today</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            {loading
              ? "Loading…"
              : `${visible.length} role${visible.length === 1 ? "" : "s"} to work through`}
            {appliedCount > 0 && ` · ${appliedCount} applied`}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setHideDone(!hideDone)}>
            {hideDone ? "Show" : "Hide"} completed
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFiltered(!showFiltered)}
          >
            {showFiltered ? "Hide" : "Show"} filtered
          </Button>
        </div>
      </div>

      {loading && <SkeletonRows rows={6} />}

      {!loading && (
      <div className="rounded-lg border divide-y">
        {visible.map((m) => (
          <div key={m.job.id} className="px-4 py-3">
            <div className="flex items-start gap-3 flex-wrap sm:flex-nowrap">
              <span
                className={`w-10 text-lg font-semibold tabular-nums ${scoreTone(m.score)}`}
                title="Fit score out of 100"
              >
                {Math.round(m.score * 100)}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <Link
                    href={`/jobs/${m.job.id}`}
                    className="font-medium hover:underline"
                  >
                    {m.job.title}
                  </Link>
                  {m.job.remote && <Badge variant="secondary">remote</Badge>}
                  {m.tier === "estimated" && (
                    <Badge
                      variant="outline"
                      title="Ranked on semantic + keyword fit; required skills not yet extracted."
                    >
                      estimated
                    </Badge>
                  )}
                  {m.hard_filtered && (
                    <Badge variant="outline">filtered: {m.filter_reason}</Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground truncate">
                  {m.job.company} · {m.job.location || "—"}
                </p>
              </div>
              <button
                onClick={() => setOpenId(openId === m.job.id ? null : m.job.id)}
                className="text-sm underline underline-offset-4 whitespace-nowrap"
              >
                {openId === m.job.id ? "Hide why" : "Why?"}
              </button>
              <Link
                href={`/jobs/${m.job.id}`}
                className="text-sm underline underline-offset-4 whitespace-nowrap"
              >
                Open
              </Link>
              <StatusSelect
                jobId={m.job.id}
                value={m.status}
                onChange={(s) => setStatus(m.job.id, s)}
                className="w-36"
              />
            </div>
            {openId === m.job.id && <FitBreakdown match={m} />}
          </div>
        ))}

        {visible.length === 0 && (
          <div className="px-4 py-8 text-center space-y-3">
            <p className="text-muted-foreground text-sm">
              {matches.length === 0
                ? "No scored jobs yet — fetch and score them from Home."
                : hideDone
                  ? "All caught up. Everything left is applied or closed."
                  : "All caught up for today."}
            </p>
            <div className="flex gap-2 justify-center">
              <Link
                href="/"
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                {matches.length === 0 ? "Fetch and score jobs" : "Back to home"}
              </Link>
              <Link
                href="/manual-jd"
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                Paste a job description
              </Link>
            </div>
          </div>
        )}
      </div>
      )}
    </div>
  );
}
