"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, type IngestionRun, type Job, type JobStats } from "@/lib/api";
import { useRemembered } from "@/lib/use-remembered";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { SkeletonRows } from "@/components/ui/skeleton";

function postedAgo(iso: string | null): string {
  if (!iso) return "—";
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "1d ago";
  return `${days}d ago`;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [stats, setStats] = useState<JobStats | null>(null);
  const [runs, setRuns] = useState<IngestionRun[]>([]);
  const [q, setQ] = useState("");
  const [showRuns, setShowRuns] = useRemembered("jobs.showRuns", false);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async (query: string) => {
    try {
      const [j, s] = await Promise.all([api.listJobs(query), api.jobStats()]);
      setJobs(j);
      setStats(s);
    } catch {
      // Backend not reachable yet — leave the table empty.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh(q);
  }, [refresh, q]);

  async function toggleRuns() {
    if (!showRuns && runs.length === 0) {
      try {
        setRuns(await api.listRuns());
      } catch {
        /* ignore */
      }
    }
    setShowRuns(!showRuns);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Jobs</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            {stats
              ? `${stats.active} active roles from ${stats.companies} companies`
              : "Loading…"}
            {stats && stats.expired > 0 ? ` · ${stats.expired} expired` : ""}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={toggleRuns}>
          {showRuns ? "Hide" : "Show"} ingestion runs
        </Button>
      </div>

      <p className="text-xs text-muted-foreground">
        Refresh the list with <strong>Fetch jobs</strong> on the{" "}
        <Link href="/" className="underline">
          home page
        </Link>
        .
      </p>

      {showRuns && (
        <div className="rounded-lg border divide-y text-sm">
          {runs.map((r) => (
            <div key={r.id} className="flex items-center gap-3 px-3 py-2">
              <span className="w-36 truncate font-medium">{r.company}</span>
              <span className="w-24 text-muted-foreground">{r.source}</span>
              <span className="text-muted-foreground">
                seen {r.jobs_seen} · new {r.jobs_new} · expired {r.jobs_expired}
              </span>
              <span className="ml-auto">
                {r.ok ? (
                  <Badge variant="secondary">ok</Badge>
                ) : (
                  <Badge variant="destructive" title={r.error ?? ""}>
                    failed
                  </Badge>
                )}
              </span>
            </div>
          ))}
          {runs.length === 0 && (
            <p className="px-3 py-2 text-muted-foreground">No runs recorded yet.</p>
          )}
        </div>
      )}

      <Separator />

      <div className="space-y-1.5">
        <Label htmlFor="job-filter">Filter</Label>
        <Input
          id="job-filter"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter by title or description…"
          className="max-w-sm"
        />
      </div>

      {loading && <SkeletonRows rows={6} />}

      {!loading && (
      <div className="rounded-lg border divide-y">
        {jobs.map((job) => (
          <div key={job.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium truncate">{job.title}</span>
                {job.remote && <Badge variant="secondary">remote</Badge>}
              </div>
              <p className="text-sm text-muted-foreground truncate">
                {job.company} · {job.location || "—"} · {job.source}
              </p>
            </div>
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {postedAgo(job.posted_at)}
            </span>
            <a
              href={job.apply_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm underline underline-offset-4 whitespace-nowrap"
            >
              Open
            </a>
          </div>
        ))}
        {jobs.length === 0 && (
          <div className="px-4 py-8 text-center space-y-3">
            <p className="text-muted-foreground text-sm">
              {q ? `Nothing matches "${q}".` : "No jobs yet."}
            </p>
            {!q && (
              <Link
                href="/"
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                Fetch jobs
              </Link>
            )}
          </div>
        )}
      </div>
      )}
    </div>
  );
}
