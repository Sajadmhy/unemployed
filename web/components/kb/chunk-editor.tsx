"use client";

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

// Editable form of a chunk. technologies/skills are comma-separated strings
// here (nicer to type) and split into arrays when saved.
export type EditableChunk = {
  type: string;
  title: string;
  context: string;
  company: string;
  date_range: string;
  accomplishment: string;
  technologies: string;
  skills: string;
  impact: string;
};

export function ChunkEditor({
  value,
  onChange,
  onRemove,
}: {
  value: EditableChunk;
  onChange: (patch: Partial<EditableChunk>) => void;
  onRemove: () => void;
}) {
  return (
    <div className="rounded-md border p-3 space-y-2 bg-muted/20">
      <div className="grid grid-cols-[10rem_1fr] gap-2">
        <Select
          value={value.type}
          onValueChange={(v) => onChange({ type: v ?? value.type })}
        >
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
        <Input
          value={value.title}
          onChange={(e) => onChange({ title: e.target.value })}
          placeholder="Title"
        />
      </div>

      <Textarea
        value={value.accomplishment}
        onChange={(e) => onChange({ accomplishment: e.target.value })}
        rows={2}
        placeholder="Accomplishment"
      />

      <div className="grid grid-cols-2 gap-2">
        <Input
          value={value.technologies}
          onChange={(e) => onChange({ technologies: e.target.value })}
          placeholder="Technologies (comma separated)"
        />
        <Input
          value={value.skills}
          onChange={(e) => onChange({ skills: e.target.value })}
          placeholder="Skills (comma separated)"
        />
      </div>

      <div className="grid grid-cols-3 gap-2">
        <Input
          value={value.context}
          onChange={(e) => onChange({ context: e.target.value })}
          placeholder="Context"
        />
        <Input
          value={value.company}
          onChange={(e) => onChange({ company: e.target.value })}
          placeholder="Company / Org"
        />
        <Input
          value={value.date_range}
          onChange={(e) => onChange({ date_range: e.target.value })}
          placeholder="Date range"
        />
      </div>

      <Input
        value={value.impact}
        onChange={(e) => onChange({ impact: e.target.value })}
        placeholder="Impact (optional)"
      />

      <div>
        <Label className="sr-only">Remove</Label>
        <Button variant="ghost" size="sm" onClick={onRemove}>
          Remove chunk
        </Button>
      </div>
    </div>
  );
}
