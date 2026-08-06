"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { avatarUrl, fetchSignups, type Signup } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

const SHOWN = 12;

/**
 * A glance at everyone else running this, on the home page.
 *
 * When the wall cannot be reached it renders nothing at all. Not an error, not
 * a retry button: an offline copy of this app should look exactly like one
 * whose wall happens to be empty, because being offline is a normal way to use
 * it and the rest of the page works regardless.
 */
export function BoardStrip() {
  const [data, setData] = useState<{ count: number; signups: Signup[] } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let current = true;
    fetchSignups(SHOWN)
      .then((result) => current && setData(result))
      .finally(() => current && setLoading(false));
    return () => {
      current = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-3">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="size-9 rounded-full" />
        ))}
      </div>
    );
  }

  if (!data || data.signups.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <div className="flex -space-x-2">
        {data.signups.slice(0, SHOWN).map((person) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={person.id}
            src={avatarUrl(person.seed, person.gender)}
            alt=""
            title={person.name}
            width={36}
            height={36}
            loading="lazy"
            className="bg-background size-9 rounded-full border"
          />
        ))}
      </div>
      <p className="text-muted-foreground text-sm">
        people running this
        {". "}
        <Link href="/board" className="underline underline-offset-4">
          See the wall
        </Link>
      </p>
    </div>
  );
}
