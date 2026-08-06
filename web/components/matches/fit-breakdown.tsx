"use client";

import type { Match } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

const LABELS: Record<string, string> = {
  required_coverage: "Required skills",
  semantic: "Semantic fit",
  preferred_coverage: "Preferred skills",
  keyword_overlap: "Keyword overlap",
  preference_fit: "Matches your preferences",
};

function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

/** Only the scoring parts, so both the list row and the job page can pass their
 *  own shape without one pretending to be the other. */
type FitLike = Pick<
  Match,
  | "f_semantic"
  | "f_keyword"
  | "f_required_cov"
  | "f_preferred_cov"
  | "f_preference_fit"
  | "confidence"
  | "why"
>;

/** The answer to "why this score?" — every number traces to a feature. */
export function FitBreakdown({ match }: { match: FitLike }) {
  const all: Record<string, number> = {
    required_coverage: match.f_required_cov,
    semantic: match.f_semantic,
    preferred_coverage: match.f_preferred_cov,
    keyword_overlap: match.f_keyword,
    preference_fit: match.f_preference_fit,
  };
  const weights = match.why.weights ?? {};
  // An estimated score is computed from a subset of features. Listing the rest
  // at "0% × 0" would read as "you scored zero" rather than "not measured yet".
  const features = Object.fromEntries(
    Object.entries(all).filter(([key]) => key in weights),
  );
  const missing = match.why.required_missing ?? [];
  const matched = match.why.required_matched ?? [];

  return (
    <div className="space-y-3 border-t pt-3 mt-3">
      <div className="space-y-1.5">
        {Object.entries(features).map(([key, value]) => (
          <div key={key} className="flex items-center gap-3 text-xs">
            <span className="w-32 text-muted-foreground">{LABELS[key]}</span>
            <div className="h-1.5 flex-1 rounded bg-muted overflow-hidden">
              <div
                className="h-full bg-foreground/70"
                style={{ width: `${Math.min(100, value * 100)}%` }}
              />
            </div>
            <span className="w-10 text-right tabular-nums">{pct(value)}</span>
            <span className="w-16 text-right text-muted-foreground">
              × {weights[key] ?? 0}
            </span>
          </div>
        ))}
      </div>

      {matched.length > 0 && (
        <div className="text-xs">
          <span className="text-muted-foreground">You have: </span>
          {matched.map((s) => (
            <Badge key={s} variant="secondary" className="mr-1 mb-1">
              {s}
            </Badge>
          ))}
        </div>
      )}

      {missing.length > 0 && (
        <div className="text-xs">
          <span className="text-muted-foreground">Missing: </span>
          {missing.slice(0, 8).map((s) => (
            <Badge key={s} variant="outline" className="mr-1 mb-1">
              {s}
            </Badge>
          ))}
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Extraction confidence {pct(match.confidence)}
        {match.why.min_years ? ` · asks for ${match.why.min_years}+ yrs` : ""}
        {match.why.seniority ? ` · ${match.why.seniority}-level` : ""}
      </p>
    </div>
  );
}
