"use client";

import { useState } from "react";
import { toast } from "sonner";
import { api, type Resume, type ResumeBullet } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

/**
 * Edits WORDS, never layout.
 *
 * The user can rewrite bullet text, drop a bullet, and adjust the skills line.
 * Sections, ordering, fonts and the PDF template stay code-owned, so no edit can
 * make the resume unparseable. Each bullet keeps its source_chunk_ids, so an
 * edited bullet is still traceable to the accomplishment it came from.
 */
export function ResumeEditor({
  resume,
  onSaved,
}: {
  resume: Resume;
  onSaved: (r: Resume) => void;
}) {
  const [bullets, setBullets] = useState<ResumeBullet[]>(resume.bullets);
  const [skills, setSkills] = useState(resume.skills.join(", "));
  const [summary, setSummary] = useState(resume.summary);
  const [saving, setSaving] = useState(false);

  function setText(index: number, text: string) {
    setBullets((prev) => prev.map((b, i) => (i === index ? { ...b, text } : b)));
  }

  async function save() {
    setSaving(true);
    try {
      const updated = await api.editResume(resume.id, {
        summary,
        skills: skills.split(",").map((s) => s.trim()).filter(Boolean),
        bullets: bullets.filter((b) => b.text.trim()),
      });
      onSaved(updated);
      toast.success("Saved — PDF and ATS check regenerated");
    } catch (e) {
      toast.error(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-medium">Edit resume</h2>
        <Button size="sm" onClick={save} disabled={saving}>
          {saving ? "Saving…" : "Save & re-check"}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        You edit the words; layout and sections stay fixed so the resume can&apos;t
        become unparseable. Each bullet keeps its source link.
      </p>

      <div className="space-y-1.5">
        <label className="text-xs text-muted-foreground">Summary (optional)</label>
        <Textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={2}
          placeholder="Leave empty to omit this section"
        />
      </div>

      <div className="space-y-1.5">
        <label className="text-xs text-muted-foreground">
          Skills (comma separated)
        </label>
        <Input value={skills} onChange={(e) => setSkills(e.target.value)} />
      </div>

      <div className="space-y-3">
        {bullets.map((b, i) => (
          <div key={i} className="space-y-1">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-muted-foreground truncate">
                {b.section} · {b.title}
              </span>
              <button
                onClick={() => setBullets((p) => p.filter((_, idx) => idx !== i))}
                className="text-xs text-muted-foreground underline shrink-0"
              >
                remove
              </button>
            </div>
            <Textarea
              value={b.text}
              onChange={(e) => setText(i, e.target.value)}
              rows={2}
            />
          </div>
        ))}
        {bullets.length === 0 && (
          <p className="text-sm text-muted-foreground">
            All bullets removed — add some back by regenerating.
          </p>
        )}
      </div>
    </div>
  );
}
