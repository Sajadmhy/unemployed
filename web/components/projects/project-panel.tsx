"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api, type ProjectIdea } from "@/lib/api";
import { Working } from "@/components/working";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

/**
 * For a fresher, shipping something relevant to the company's product is the
 * strongest signal available — it is evidence rather than a claim, and attached
 * to an outreach message it is the thing most likely to earn a reply.
 *
 * The idea targets the skills this job wants that your knowledge base cannot yet
 * prove, so building it closes a real gap rather than padding the portfolio.
 */
export function ProjectPanel({ jobId }: { jobId: number }) {
  const [idea, setIdea] = useState<ProjectIdea | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setIdea(await api.projectIdea(jobId));
    } catch {
      /* backend not reachable */
    }
  }, [jobId]);

  useEffect(() => {
    load();
  }, [load]);

  async function generate() {
    setBusy(true);
    try {
      setIdea(await api.generateProjectIdea(jobId));
      toast.success("Project idea ready");
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-medium">Build something for them</h2>
        <Button size="sm" variant="outline" onClick={generate} disabled={busy}>
          {busy ? "Designing…" : idea ? "New idea" : "Suggest a project"}
        </Button>
      </div>

      {busy && <Working label="Designing a project around the skills this role wants" />}

      {!idea && (
        <p className="text-sm text-muted-foreground">
          Designs one project specific to this company that targets the skills
          this role wants but your knowledge base can&apos;t yet prove — something
          worth attaching when you reach out.
        </p>
      )}

      {idea && (
        <div className="space-y-3 text-sm">
          <div>
            <p className="font-medium">{idea.title}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Scope: {idea.scope}
            </p>
          </div>

          {idea.problem && (
            <div>
              <p className="text-xs text-muted-foreground">Problem</p>
              <p>{idea.problem}</p>
            </div>
          )}

          <div>
            <p className="text-xs text-muted-foreground">What to build</p>
            <p>{idea.what_to_build}</p>
          </div>

          {idea.why_it_impresses && (
            <div>
              <p className="text-xs text-muted-foreground">Why it lands</p>
              <p>{idea.why_it_impresses}</p>
            </div>
          )}

          {(idea.tech_stack.length > 0 || idea.covers_gaps.length > 0) && (
            <div className="flex flex-wrap gap-1 pt-1">
              {idea.tech_stack.map((t) => (
                <Badge key={t} variant="secondary">
                  {t}
                </Badge>
              ))}
              {idea.covers_gaps.map((g) => (
                <Badge key={g} variant="outline" title="A skill this role wants that your KB can't yet show">
                  closes gap: {g}
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
