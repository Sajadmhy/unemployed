"use client";

import { useMemo, useState } from "react";

import { copy } from "@/lib/copy";
import { RESULTS, ROUND_TYPES, ROUND_OUTCOMES } from "@/lib/validate";
import type { ExperienceRow } from "@/lib/db";

type DraftRound = { round_type: string; description: string; outcome: string };

function emptyRound(): DraftRound {
  return { round_type: ROUND_TYPES[0], description: "", outcome: "pending" };
}

/**
 * Reuses the same localStorage client id as signup-form.tsx: posting an
 * experience is tied to the identity someone already made when they joined
 * the wall, not a new account.
 *
 * Whether someone is allowed to post at all is the caller's business, not this
 * component's: it renders inside a dialog that is only reachable once you have
 * joined, so a second gate here would be dead code behind a locked door.
 */
export function ExperienceForm({
  onPosted,
  initialData,
}: {
  onPosted: (experience: ExperienceRow) => void;
  initialData?: ExperienceRow;
}) {
  const [company, setCompany] = useState(initialData?.company || "");
  const [role, setRole] = useState(initialData?.role || "");
  const [result, setResult] = useState<(typeof RESULTS)[number]>(
    (initialData?.result as (typeof RESULTS)[number]) || "offer"
  );
  const [summary, setSummary] = useState(initialData?.summary || "");
  const [rounds, setRounds] = useState<DraftRound[]>(
    initialData?.rounds?.length
      ? initialData.rounds.map((r) => ({
          round_type: r.round_type,
          description: r.description,
          outcome: r.outcome,
        }))
      : [emptyRound()]
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clientId = useMemo(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("unemployed:client");
  }, []);

  function updateRound(i: number, patch: Partial<DraftRound>) {
    setRounds((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(initialData ? `/api/experiences/${initialData.id}` : "/api/experiences", {
        method: initialData ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clientId, company, role, result, summary, rounds }),
      });
      const data = await res.json();
      if (!res.ok) {
        const key = data.error as keyof typeof copy.experiences.form.errors;
        setError(copy.experiences.form.errors[key] ?? copy.experiences.form.errors.generic);
        return;
      }
      // The parent closes the dialog and prepends this to the board, so the
      // post is visible immediately without a refetch.
      onPosted({
        id: initialData ? initialData.id : String(data.id),
        company,
        role,
        result,
        summary,
        created_at: initialData ? initialData.created_at : new Date().toISOString(),
        signup_id: initialData ? initialData.signup_id : String(data.signup_id),
        name: initialData ? initialData.name : data.name,
        seed: initialData ? initialData.seed : data.seed,
        gender: initialData ? initialData.gender : data.gender,
        rounds: rounds.map((r, i) => ({ ...r, round_number: i + 1 })),
      });
    } catch {
      setError(copy.experiences.form.errors.generic);
    } finally {
      setBusy(false);
    }
  }

  const canSubmit =
    company.trim().length > 0 &&
    role.trim().length > 0 &&
    summary.trim().length > 0 &&
    rounds.every((r) => r.description.trim().length > 0);

  return (
    // No card border: the dialog is already the container.
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={copy.experiences.form.companyLabel}>
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder={copy.experiences.form.companyPlaceholder}
            className="input"
          />
        </Field>
        <Field label={copy.experiences.form.roleLabel}>
          <input
            value={role}
            onChange={(e) => setRole(e.target.value)}
            placeholder={copy.experiences.form.rolePlaceholder}
            className="input"
          />
        </Field>
        <Field label={copy.experiences.form.resultLabel}>
          <select
            value={result}
            onChange={(e) => setResult(e.target.value as (typeof RESULTS)[number])}
            className="input"
          >
            {RESULTS.map((r) => (
              <option key={r} value={r}>
                {copy.experiences.resultLabels[r]}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <Field label={copy.experiences.form.summaryLabel}>
        <textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          placeholder={copy.experiences.form.summaryPlaceholder}
          rows={3}
          className="input resize-none"
        />
      </Field>

      <div className="space-y-4">
        <p className="text-sm font-medium">{copy.experiences.form.roundsLabel}</p>
        {rounds.map((round, i) => (
          <div key={i} className="grid gap-3 rounded-md border p-3 sm:grid-cols-3">
            <Field label={copy.experiences.form.roundTypeLabel}>
              <select
                value={round.round_type}
                onChange={(e) => updateRound(i, { round_type: e.target.value })}
                className="input"
              >
                {ROUND_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {copy.experiences.roundTypeLabels[t]}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={copy.experiences.form.roundOutcomeLabel}>
              <select
                value={round.outcome}
                onChange={(e) => updateRound(i, { outcome: e.target.value })}
                className="input"
              >
                {ROUND_OUTCOMES.map((o) => (
                  <option key={o} value={o}>
                    {copy.experiences.outcomeLabels[o]}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={copy.experiences.form.roundDescriptionLabel}>
              <input
                value={round.description}
                onChange={(e) => updateRound(i, { description: e.target.value })}
                className="input"
              />
            </Field>
            {rounds.length > 1 && (
              <button
                type="button"
                onClick={() => setRounds((prev) => prev.filter((_, idx) => idx !== i))}
                className="text-muted-foreground hover:text-foreground col-span-full text-left text-xs underline underline-offset-4"
              >
                {copy.experiences.form.removeRound}
              </button>
            )}
          </div>
        ))}
        <button
          type="button"
          onClick={() => setRounds((prev) => [...prev, emptyRound()])}
          className="rounded-md border px-3 py-1.5 text-xs hover:bg-muted"
        >
          {copy.experiences.form.addRound}
        </button>
      </div>

      {error && (
        <p className="rounded-md border px-3 py-2 text-sm font-medium" role="alert">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={submit}
        disabled={busy || !canSubmit}
        className="rounded-lg border border-foreground bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-40"
      >
        {busy ? copy.experiences.form.submitting : copy.experiences.form.submit}
      </button>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1.5 text-sm">
      <span className="font-medium">{label}</span>
      {children}
    </label>
  );
}
