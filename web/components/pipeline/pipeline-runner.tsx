"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api, type PipelineKind, type PipelineRun } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { GoBackTo } from "@/components/go-back-to";
import { ProgressBar } from "@/components/ui/progress-bar";

const ACTIONS: { kind: PipelineKind; label: string; hint: string }[] = [
  { kind: "ingest", label: "Fetch jobs", hint: "~10 min, scores them too" },
  { kind: "discover", label: "Find companies", hint: "~5 min" },
];

/**
 * Runs the long pipeline steps without a terminal.
 *
 * There is no separate "score" button: fetching without scoring leaves the app
 * in a state where nothing is rankable and nothing looks wrong, which is a
 * choice no user should have to make. Fetch does both.
 *
 * The server allows only one run at a time and returns 409 otherwise, so the
 * buttons disable while anything is in flight.
 */
export function PipelineRunner({ onFinished }: { onFinished?: () => void }) {
  const [run, setRun] = useState<PipelineRun | null>(null);
  const wasRunning = useRef(false);

  const poll = useCallback(async () => {
    try {
      const current = await api.pipelineStatus();
      setRun(current);
      if (wasRunning.current && current?.status !== "running") {
        wasRunning.current = false;
        if (current?.status === "failed") toast.error(current.error ?? "Run failed");
        else toast.success("Finished");
        onFinished?.();
      }
      wasRunning.current = current?.status === "running";
    } catch {
      /* backend not reachable */
    }
  }, [onFinished]);

  useEffect(() => {
    poll();
    // 2s is responsive enough for a job measured in minutes, and cheap.
    const timer = setInterval(poll, 2000);
    return () => clearInterval(timer);
  }, [poll]);

  async function start(kind: PipelineKind) {
    try {
      setRun(await api.startPipeline(kind));
      wasRunning.current = true;
    } catch (e) {
      toast.error(String(e).includes("409") ? "Something is already running" : String(e));
    }
  }

  const running = run?.status === "running";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {ACTIONS.map((a) => (
          <Button
            key={a.kind}
            variant={a.kind === "ingest" ? "default" : "outline"}
            onClick={() => start(a.kind)}
            disabled={running}
          >
            {running && run?.kind === a.kind ? "Running…" : a.label}
            <span className="text-muted-foreground ml-1.5 text-xs">{a.hint}</span>
          </Button>
        ))}
      </div>

      {running && (
        <div className="space-y-1.5">
          <ProgressBar done={run.done} total={run.total} message={run.message} />
          <p className="text-xs text-muted-foreground">
            This takes a while — your own machine is reading every posting. Keep
            this tab open; the rest of the app still works.
          </p>
          <GoBackTo />
        </div>
      )}

      {!running && run?.status === "failed" && (
        <p className="text-xs text-amber-600 dark:text-amber-500">⚠ {run.error}</p>
      )}
    </div>
  );
}
