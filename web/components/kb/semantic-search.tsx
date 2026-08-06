"use client";

import { useState } from "react";
import { api, type SearchResult } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// A small demo of the core primitive: retrieval by meaning. Type a role/skill
// phrase and see which of your accomplishments surface, ranked by similarity.
export function SemanticSearch() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    if (!q.trim()) return;
    setLoading(true);
    try {
      setResults(await api.search(q.trim(), 5));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border p-5 space-y-3">
      <h2 className="font-medium">Try semantic search</h2>
      <p className="text-sm text-muted-foreground">
        Search by meaning, not keywords — e.g. “scalable backend infrastructure”.
      </p>
      <div className="flex gap-2">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="Describe a role or skill…"
        />
        <Button onClick={run} disabled={loading}>
          {loading ? "…" : "Search"}
        </Button>
      </div>
      {results && (
        <div className="space-y-2 pt-1">
          {results.length === 0 && (
            <p className="text-sm text-muted-foreground">No chunks to search.</p>
          )}
          {results.map((r) => (
            <div key={r.id} className="flex items-center gap-3 text-sm">
              <span className="font-mono text-xs w-12 shrink-0 text-right">
                {r.similarity.toFixed(3)}
              </span>
              <span className="truncate">{r.accomplishment}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
