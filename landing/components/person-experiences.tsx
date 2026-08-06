"use client";

import { useEffect, useState } from "react";

import { AvatarImage } from "./avatar";
import { ExperienceCard } from "./experience-card";
import { Modal } from "./modal";
import { countryName } from "@/lib/countries";
import { copy } from "@/lib/copy";
import type { ExperienceRow, SignupRow } from "@/lib/db";

/**
 * One person's interview experiences, shown on the wall itself.
 *
 * Deliberately not a link to /experiences: the question being asked here is
 * "who is this person and what have they been through", and answering it by
 * navigating to a list of everybody's posts, scrolled to nothing in particular,
 * loses the thread. The fetch is by signup id so this stays one small request
 * rather than pulling the whole board down to filter it in the browser.
 */
export function PersonExperiences({
  person,
  onClose,
}: {
  person: SignupRow | null;
  onClose: () => void;
}) {
  // What was fetched, tagged with who it was fetched for. Storing the owner
  // alongside the rows is what makes "loading" a derived value rather than a
  // second piece of state that has to be reset in the effect: opening someone
  // new makes the tag stop matching, which reads as loading until their rows
  // arrive. Without the tag, the previous person's posts flash up under the
  // new person's name.
  const [loaded, setLoaded] = useState<{ personId: string; rows: ExperienceRow[] } | null>(null);

  useEffect(() => {
    if (!person) return;
    let cancelled = false;

    fetch(`/api/experiences?signupId=${encodeURIComponent(person.id)}`)
      .then((res) => (res.ok ? res.json() : { experiences: [] }))
      .then((data) => {
        if (!cancelled) {
          setLoaded({ personId: person.id, rows: data.experiences as ExperienceRow[] });
        }
      })
      .catch(() => {
        // An empty list rather than an error state: the panel is about a person,
        // and "nothing here" is the honest answer when we cannot reach the board.
        if (!cancelled) setLoaded({ personId: person.id, rows: [] });
      });

    return () => {
      cancelled = true;
    };
  }, [person]);

  const experiences = person && loaded?.personId === person.id ? loaded.rows : null;

  return (
    <Modal open={person !== null} onClose={onClose} title={person?.name ?? ""}>
      {person && (
        <>
          <div className="flex items-center gap-4">
            <AvatarImage seed={person.seed} gender={person.gender} />
            <div className="min-w-0">
              <p className="truncate font-medium">{person.name}</p>
              <p className="text-muted-foreground truncate text-sm">
                {countryName(person.country)}
              </p>
            </div>
          </div>

          <div className="mt-6">
            {experiences === null ? (
              <p className="text-muted-foreground text-sm">{copy.wall.personLoading}</p>
            ) : experiences.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                {copy.wall.personEmpty(person.name)}
              </p>
            ) : (
              <>
                <p className="text-muted-foreground mb-4 text-sm">
                  {copy.wall.personCount(experiences.length)}
                </p>
                <ul className="space-y-2">
                  {experiences.map((experience) => (
                    <ExperienceCard key={experience.id} experience={experience} collapsible />
                  ))}
                </ul>
              </>
            )}
          </div>
        </>
      )}
    </Modal>
  );
}
