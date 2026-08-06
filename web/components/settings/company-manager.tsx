"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api, type CompanyRow, type CompanySearchResult } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/**
 * Add any company with a public job board.
 *
 * Typing a name probes Greenhouse, Lever, Ashby and SmartRecruiters live and
 * reports which one hosts it — so coverage isn't limited to the shipped seed
 * list. A board only counts if it actually has jobs for your region: slugs
 * collide across vendors, and a same-named company elsewhere is not a match.
 */
export function CompanyManager() {
  const [companies, setCompanies] = useState<CompanyRow[]>([]);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<CompanySearchResult | null>(null);
  const [searching, setSearching] = useState(false);

  const load = useCallback(async () => {
    try {
      setCompanies(await api.listCompanies());
    } catch {
      /* backend not reachable */
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function search() {
    if (query.trim().length < 2) return toast.error("Enter a company name");
    setSearching(true);
    setResult(null);
    try {
      setResult(await api.searchCompany(query.trim()));
    } catch (e) {
      toast.error(String(e));
    } finally {
      setSearching(false);
    }
  }

  async function add() {
    if (!result?.found) return;
    try {
      await api.addCompany({
        source: result.source!,
        token: result.token!,
        name: result.name,
        matched_jobs: result.matched_jobs ?? 0,
      });
      toast.success(`Added ${result.name} — run a fetch to pull its jobs`);
      setResult(null);
      setQuery("");
      load();
    } catch (e) {
      toast.error(String(e));
    }
  }

  async function remove(company: CompanyRow) {
    if (!confirm(`Stop tracking ${company.name}? Its jobs stop being fetched.`)) return;
    try {
      await api.removeCompany(company.id);
      toast.success(`Removed ${company.name}`);
      load();
    } catch (e) {
      toast.error(String(e));
    }
  }

  return (
    <div className="rounded-lg border p-5 space-y-4">
      <div>
        <h2 className="font-medium">Companies</h2>
        <p className="text-xs text-muted-foreground mt-1">
          {companies.length} tracked. Search for any company — if it has a public
          board on Greenhouse, Lever, Ashby or SmartRecruiters, you can add it.
        </p>
      </div>

      <div className="flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          placeholder="e.g. Razorpay, Stripe, Zomato…"
        />
        <Button onClick={search} disabled={searching}>
          {searching ? "Searching…" : "Search"}
        </Button>
      </div>

      {result && (
        <div className="rounded-md border p-3 text-sm">
          {result.found ? (
            <div className="flex items-center gap-3 flex-wrap">
              <span className="font-medium">{result.name}</span>
              <Badge variant="secondary">{result.source}</Badge>
              <span className="text-muted-foreground text-xs">
                {result.matched_jobs} matching job
                {result.matched_jobs === 1 ? "" : "s"} of {result.total_jobs}
              </span>
              {result.already_tracked ? (
                <Badge variant="outline">already tracked</Badge>
              ) : (
                <Button size="sm" onClick={add}>
                  Add
                </Button>
              )}
            </div>
          ) : (
            <p className="text-muted-foreground">
              No public board found for &ldquo;{result.name}&rdquo; with jobs in your
              region. They may use a different ATS, or post nothing there right now.
            </p>
          )}
        </div>
      )}

      <div className="max-h-72 overflow-y-auto rounded-md border divide-y">
        {companies.map((c) => (
          <div key={c.id} className="flex items-center gap-3 px-3 py-2 text-sm">
            <span className="flex-1 truncate">{c.name}</span>
            <Badge variant="secondary">{c.source}</Badge>
            <span className="text-xs text-muted-foreground w-20 text-right">
              {c.active_jobs} job{c.active_jobs === 1 ? "" : "s"}
            </span>
            <button
              onClick={() => remove(c)}
              className="text-xs text-muted-foreground underline shrink-0"
            >
              remove
            </button>
          </div>
        ))}
        {companies.length === 0 && (
          <p className="px-3 py-4 text-sm text-muted-foreground">
            No companies yet. Search above, or run{" "}
            <code className="bg-muted px-1 rounded">
              python -m app.ingestion.discover
            </code>
            .
          </p>
        )}
      </div>
    </div>
  );
}
