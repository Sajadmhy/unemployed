"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

/**
 * Second entry point: a job the user found on LinkedIn, Naukri, a referral, etc.
 * It joins the same pipeline as ingested jobs — identical extraction, scoring and
 * resume generation — so nothing about the workflow changes.
 */
export default function ManualJdPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    title: "",
    company: "",
    location: "",
    apply_url: "",
    description: "",
  });
  const [busy, setBusy] = useState(false);

  function set(patch: Partial<typeof form>) {
    setForm((f) => ({ ...f, ...patch }));
  }

  async function submit() {
    if (!form.title.trim() || !form.company.trim()) {
      return toast.error("Title and company are required");
    }
    if (form.description.trim().length < 50) {
      return toast.error("Paste the full job description (at least 50 characters)");
    }
    setBusy(true);
    try {
      const { job_id } = await api.createManualJob(form);
      toast.success("Scored — opening the job");
      router.push(`/jobs/${job_id}`);
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold">Paste a job description</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          For roles you found yourself. It gets the same requirement extraction,
          fit score and tailored resume as automatically discovered jobs.
        </p>
      </div>

      <div className="rounded-lg border p-5 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label>Job title</Label>
            <Input
              value={form.title}
              onChange={(e) => set({ title: e.target.value })}
              placeholder="Software Engineer, Backend"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Company</Label>
            <Input
              value={form.company}
              onChange={(e) => set({ company: e.target.value })}
              placeholder="Razorpay"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Location</Label>
            <Input
              value={form.location}
              onChange={(e) => set({ location: e.target.value })}
              placeholder="Bengaluru, India"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Application URL</Label>
            <Input
              value={form.apply_url}
              onChange={(e) => set({ apply_url: e.target.value })}
              placeholder="https://…"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <Label>Job description</Label>
          <Textarea
            value={form.description}
            onChange={(e) => set({ description: e.target.value })}
            rows={12}
            placeholder="Paste the full description — responsibilities, requirements, everything."
          />
        </div>

        <Button onClick={submit} disabled={busy}>
          {busy ? "Extracting & scoring… (~30s)" : "Score this job"}
        </Button>
      </div>
    </div>
  );
}
