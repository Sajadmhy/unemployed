"use client";

import { toast } from "sonner";
import { api, type KBChunk } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function ChunkList({
  chunks,
  onChanged,
}: {
  chunks: KBChunk[];
  onChanged: () => void;
}) {
  async function remove(chunk: KBChunk) {
    // A chunk is hand-curated evidence and there is no undo — ask first.
    if (!confirm(`Delete "${chunk.title}"? This cannot be undone.`)) return;
    try {
      await api.deleteChunk(chunk.id);
      toast.success("Deleted");
      onChanged();
    } catch (e) {
      toast.error(String(e));
    }
  }

  if (chunks.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No chunks yet — import your resume above, or add a career item by hand.
        Nothing can be written about you until there is something here.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {chunks.map((c) => (
        <div key={c.id} className="rounded-md border p-3 space-y-2">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{c.type}</Badge>
                <span className="font-medium">{c.title}</span>
                {c.date_range && (
                  <span className="text-xs text-muted-foreground">
                    {c.date_range}
                  </span>
                )}
              </div>
              <p className="text-sm mt-1">{c.accomplishment}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => remove(c)}>
              Delete
            </Button>
          </div>
          {(c.technologies.length > 0 || c.impact) && (
            <div className="flex flex-wrap items-center gap-1.5">
              {c.technologies.map((t) => (
                <Badge key={t} variant="outline" className="text-xs">
                  {t}
                </Badge>
              ))}
              {c.impact && (
                <span className="text-xs text-muted-foreground ml-1">
                  · {c.impact}
                </span>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
