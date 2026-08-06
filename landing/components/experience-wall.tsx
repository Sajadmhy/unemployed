"use client";

import { useState } from "react";
import Link from "next/link";

import { ExperienceCard } from "./experience-card";
import { ExperienceForm } from "./experience-form";
import { Modal } from "./modal";
import { usePeople } from "./people-provider";
import { copy } from "@/lib/copy";
import type { ExperienceRow } from "@/lib/db";

export function ExperienceWall({ fromServer }: { fromServer: ExperienceRow[] }) {
  const { joined } = usePeople();
  const [experiences, setExperiences] = useState(fromServer);
  const [company, setCompany] = useState("");
  const [loading, setLoading] = useState(false);
  const [composing, setComposing] = useState(false);

  async function applyFilter(value: string) {
    setCompany(value);
    setLoading(true);
    try {
      const res = await fetch(`/api/experiences?company=${encodeURIComponent(value)}`);
      const data = await res.json();
      if (res.ok) setExperiences(data.experiences as ExperienceRow[]);
    } catch {
      // Keep whatever was showing; the filter just didn't update this time.
    } finally {
      setLoading(false);
    }
  }

  function onPosted(experience: ExperienceRow) {
    setExperiences((prev) => [experience, ...prev]);
  }

  return (
    <>
      <section className="pt-28 px-6 md:px-12 lg:px-24">
        <div className="mx-auto w-full max-w-3xl">
          <p className="text-muted-foreground font-mono text-[11px] tracking-[0.2em] uppercase">
            {copy.experiences.label}
          </p>
          <h1 className="mt-5 font-serif text-3xl leading-tight sm:text-4xl">
            {copy.experiences.heading}
          </h1>
          <p className="text-muted-foreground mt-4 text-base leading-relaxed">
            {copy.experiences.body}
          </p>

          {/* The form is behind a button rather than sitting open above the
              board: most people arrive here to read, and a long empty form
              pushes everything they came for below the fold. */}
          <div className="mt-8">
            {joined ? (
              <button type="button" onClick={() => setComposing(true)} className="btn-solid">
                {copy.experiences.postCta}
              </button>
            ) : (
              <div className="card flex flex-col items-start gap-4">
                <p className="text-base">{copy.experiences.locked}</p>
                <Link href="/join" className="btn-solid">
                  {copy.join.submit}
                </Link>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="pt-14 pb-32 px-6 md:px-12 lg:px-24">
        <div className="mx-auto w-full max-w-3xl">
          <label className="block max-w-xs space-y-1.5 text-sm">
            <span className="font-medium">{copy.experiences.filterLabel}</span>
            <input
              value={company}
              onChange={(e) => applyFilter(e.target.value)}
              placeholder={copy.experiences.filterPlaceholder}
              className="input"
            />
          </label>

          <ul className="mt-8 space-y-4">
            {experiences.length === 0 && !loading && (
              <p className="text-muted-foreground text-sm">
                {company ? copy.experiences.noMatches(company) : copy.experiences.empty}
              </p>
            )}
            {experiences.map((experience) => (
              <ExperienceCard key={experience.id} experience={experience} />
            ))}
          </ul>
        </div>
      </section>

      <Modal
        open={composing}
        onClose={() => setComposing(false)}
        title={copy.experiences.postCta}
      >
        <ExperienceForm
          onPosted={(experience) => {
            onPosted(experience);
            setComposing(false);
          }}
        />
      </Modal>
    </>
  );
}
