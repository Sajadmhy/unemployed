"use client";

import { useState } from "react";

import { AvatarImage } from "./avatar";
import { copy } from "@/lib/copy";
import type { ExperienceRow } from "@/lib/db";

/**
 * One posted interview experience.
 *
 * `collapsible` is for lists where the reader is scanning rather than reading:
 * on a person's panel there may be a dozen of these, and a dozen full cards is
 * a wall of text you have to scroll past to find the company you cared about.
 * Collapsed, each one is a single line with the company and how it ended, and
 * opening one shows everything including the rounds. The board at /experiences
 * is the opposite case, one company per card and few of them, so it stays open.
 */
export function ExperienceCard({
  experience,
  collapsible = false,
  onEdit,
  onDelete,
}: {
  experience: ExperienceRow;
  collapsible?: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
}) {
  const [open, setOpen] = useState(!collapsible);
  const [showRounds, setShowRounds] = useState(false);
  const [flagged, setFlagged] = useState(false);

  async function flag() {
    if (flagged) return;
    setFlagged(true);
    try {
      await fetch("/api/experiences/flag", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ experienceId: Number(experience.id) }),
      });
    } catch {
      // The button already reads "reported"; a failed request isn't worth
      // surfacing to someone who's just trying to flag a post.
    }
  }

  const result = (
    <span className="rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap">
      {copy.experiences.resultLabels[experience.result as keyof typeof copy.experiences.resultLabels]}
    </span>
  );

  // Collapsed: the company, how it ended, and nothing else.
  if (collapsible && !open) {
    return (
      <li>
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-expanded={false}
          className="hover:bg-muted/60 flex w-full items-center justify-between gap-3 rounded-lg border px-4 py-3 text-left transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
        >
          <span className="min-w-0 flex-1">
            <span className="block truncate font-serif text-lg leading-tight">
              {experience.company}
            </span>
            <span className="text-muted-foreground block truncate text-xs">
              {experience.role}
            </span>
          </span>
          {result}
        </button>
      </li>
    );
  }

  return (
    <li className="card">
      <div className="flex items-start gap-3">
        {!collapsible && (
          <AvatarImage seed={experience.seed} gender={experience.gender} size={40} />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
            {collapsible ? (
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-expanded
                className="min-w-0 rounded-sm text-left focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
              >
                <h3 className="truncate font-serif text-xl leading-tight">
                  {experience.company}
                </h3>
              </button>
            ) : (
              <h3 className="font-serif text-xl leading-tight">{experience.company}</h3>
            )}
            {result}
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            {experience.role} &middot; {experience.name}
          </p>
          <p className="mt-3 text-sm leading-relaxed">{experience.summary}</p>

          {/* Inside a person's panel the rounds are the point of opening it, so
              they come with the card rather than behind a second click. */}
          {collapsible ? (
            <Rounds rounds={experience.rounds} />
          ) : (
            <>
              <button
                type="button"
                onClick={() => setShowRounds((v) => !v)}
                className="text-muted-foreground hover:text-foreground mt-3 text-xs underline underline-offset-4"
              >
                {showRounds ? copy.experiences.hideRounds : copy.experiences.roundCount(experience.rounds.length)}
              </button>
              {showRounds && <Rounds rounds={experience.rounds} />}
            </>
          )}

          <div className="mt-4 flex items-center justify-between">
            <span className="text-muted-foreground text-[11px]">
              {new Date(experience.created_at).toLocaleDateString()}
            </span>
            <div className="flex items-center gap-4">
              {onEdit && (
                <button type="button" onClick={onEdit} className="text-muted-foreground hover:text-foreground text-xs">
                  Edit
                </button>
              )}
              {onDelete && (
                <button type="button" onClick={onDelete} className="text-muted-foreground hover:text-destructive text-xs">
                  Delete
                </button>
              )}
              {!onEdit && !onDelete && (
                <button
                  type="button"
                  onClick={flag}
                  disabled={flagged}
                  className="text-muted-foreground hover:text-foreground text-xs disabled:opacity-50"
                >
                  {flagged ? copy.experiences.flagged : copy.experiences.flag}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </li>
  );
}

function Rounds({ rounds }: { rounds: ExperienceRow["rounds"] }) {
  if (rounds.length === 0) return null;
  return (
    <ol className="mt-3 space-y-3 border-l pl-4">
      {rounds.map((round) => (
        <li key={round.round_number}>
          <div className="flex flex-wrap items-baseline gap-x-2 text-xs">
            <span className="font-medium">
              {String(round.round_number).padStart(2, "0")}.{" "}
              {copy.experiences.roundTypeLabels[round.round_type as keyof typeof copy.experiences.roundTypeLabels]}
            </span>
            <span className="text-muted-foreground">
              {copy.experiences.outcomeLabels[round.outcome as keyof typeof copy.experiences.outcomeLabels]}
            </span>
          </div>
          <p className="text-muted-foreground mt-1 text-sm leading-relaxed">
            {round.description}
          </p>
        </li>
      ))}
    </ol>
  );
}
