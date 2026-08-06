"use client";

import { useState } from "react";
import { toast } from "sonner";
import { api, type KBItemIn } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const TYPES = [
  "project",
  "experience",
  "leadership",
  "achievement",
  "skill",
  "certification",
];

// One accomplishment row in the form. tech/skills are comma-separated text
// here and split into arrays on submit.
type AccRow = { text: string; technologies: string; skills: string; impact: string };

const emptyAcc = (): AccRow => ({ text: "", technologies: "", skills: "", impact: "" });

function splitCsv(s: string): string[] {
  return s.split(",").map((x) => x.trim()).filter(Boolean);
}

export function AddItemForm({ onAdded }: { onAdded: () => void }) {
  const [type, setType] = useState("project");
  const [title, setTitle] = useState("");
  const [context, setContext] = useState("");
  const [company, setCompany] = useState("");
  const [dateRange, setDateRange] = useState("");
  const [accs, setAccs] = useState<AccRow[]>([emptyAcc()]);
  const [saving, setSaving] = useState(false);

  function updateAcc(i: number, patch: Partial<AccRow>) {
    setAccs((prev) => prev.map((a, idx) => (idx === i ? { ...a, ...patch } : a)));
  }

  async function submit() {
    if (!title.trim()) return toast.error("Title is required");
    const filled = accs.filter((a) => a.text.trim());
    if (filled.length === 0) return toast.error("Add at least one accomplishment");

    const payload: KBItemIn = {
      type,
      title: title.trim(),
      context: context.trim() || null,
      company: company.trim() || null,
      date_range: dateRange.trim() || null,
      accomplishments: filled.map((a) => ({
        text: a.text.trim(),
        technologies: splitCsv(a.technologies),
        skills: splitCsv(a.skills),
        impact: a.impact.trim() || null,
      })),
    };

    setSaving(true);
    try {
      const created = await api.addItem(payload);
      toast.success(`Added ${created.length} chunk(s)`);
      setTitle("");
      setContext("");
      setCompany("");
      setDateRange("");
      setAccs([emptyAcc()]);
      onAdded();
    } catch (e) {
      toast.error(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-lg border p-5 space-y-4">
      <h2 className="font-medium">Add a career item</h2>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label>Type</Label>
          <Select value={type} onValueChange={(v) => setType(v ?? type)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label>Title</Label>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Real-time chat app"
          />
        </div>
        <div className="space-y-1">
          <Label>Context</Label>
          <Input
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="Solo college project"
          />
        </div>
        <div className="space-y-1">
          <Label>Company / Org</Label>
          <Input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="(optional)"
          />
        </div>
        <div className="space-y-1">
          <Label>Date range</Label>
          <Input
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            placeholder="2024"
          />
        </div>
      </div>

      <div className="space-y-3">
        <Label>Accomplishments (each becomes one searchable chunk)</Label>
        {accs.map((a, i) => (
          <div key={i} className="rounded-md border p-3 space-y-2 bg-muted/30">
            <Textarea
              value={a.text}
              onChange={(e) => updateAcc(i, { text: e.target.value })}
              placeholder="Built a WebSocket server handling 200+ concurrent users"
              rows={2}
            />
            <div className="grid grid-cols-2 gap-2">
              <Input
                value={a.technologies}
                onChange={(e) => updateAcc(i, { technologies: e.target.value })}
                placeholder="Technologies (comma separated)"
              />
              <Input
                value={a.skills}
                onChange={(e) => updateAcc(i, { skills: e.target.value })}
                placeholder="Skills (comma separated)"
              />
            </div>
            <Input
              value={a.impact}
              onChange={(e) => updateAcc(i, { impact: e.target.value })}
              placeholder="Impact (optional): Used by 3 student clubs"
            />
            {accs.length > 1 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setAccs((p) => p.filter((_, idx) => idx !== i))}
              >
                Remove
              </Button>
            )}
          </div>
        ))}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setAccs((p) => [...p, emptyAcc()])}
        >
          + Add accomplishment
        </Button>
      </div>

      <Button onClick={submit} disabled={saving}>
        {saving ? "Saving…" : "Save to Knowledge Base"}
      </Button>
    </div>
  );
}
