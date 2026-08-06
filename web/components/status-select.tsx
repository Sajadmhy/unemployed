"use client";

import { toast } from "sonner";
import { api, STATUSES, type Status } from "@/lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const LABELS: Record<Status, string> = {
  todo: "To do",
  resume_ready: "Resume ready",
  applied: "Applied",
  outreach_sent: "Outreach sent",
  closed: "Closed",
};

/** Where this job sits in the funnel. Survives re-ingest, so the daily list
 *  shows what is left to do rather than the same jobs every morning. */
export function StatusSelect({
  jobId,
  value,
  onChange,
  className,
}: {
  jobId: number;
  value: Status;
  onChange: (s: Status) => void;
  className?: string;
}) {
  async function set(next: string | null) {
    if (next === null) return; // the Select can clear itself; a job always has a status
    const status = next as Status;
    onChange(status); // optimistic: the UI should not wait on a round trip
    try {
      await api.setStatus(jobId, status);
    } catch (e) {
      toast.error(String(e));
    }
  }

  return (
    <Select value={value} onValueChange={set}>
      <SelectTrigger className={className ?? "w-40"} size="sm">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {STATUSES.map((s) => (
          <SelectItem key={s} value={s}>
            {LABELS[s]}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
