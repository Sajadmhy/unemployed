"use client";

import { useCallback, useEffect, useState } from "react";

import { avatarUrl, fetchSignups, wallUrl, type Signup } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Everyone else running this tool.
 *
 * The data comes from the hosted landing page, not the local backend, so this
 * is the one page here that needs the internet. Unlike the strip on the home
 * page it says so when it cannot connect, because you came here on purpose and
 * an empty screen would read as a bug.
 */
export default function BoardPage() {
  const [data, setData] = useState<{ count: number; signups: Signup[] } | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setData(await fetchSignups(500));
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-3xl">The wall</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          {loading
            ? "Loading the wall"
            : data
              ? `${data.count} ${data.count === 1 ? "person is" : "people are"} running this`
              : "Everyone who has put themselves on the wall"}
        </p>
      </div>

      {loading && (
        <div className="grid grid-cols-4 gap-4 sm:grid-cols-8">
          {Array.from({ length: 16 }, (_, i) => (
            <Skeleton key={i} className="size-14 rounded-full" />
          ))}
        </div>
      )}

      {!loading && !data && (
        <div className="space-y-3 rounded-lg border px-4 py-8 text-center">
          <p className="text-muted-foreground text-sm">
            Cannot reach the wall. It lives online, and the rest of this app does not,
            so everything else keeps working.
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            <Button variant="outline" size="sm" onClick={load}>
              Try again
            </Button>
            <Button
              variant="outline"
              size="sm"
              nativeButton={false}
              render={<a href={wallUrl()} target="_blank" rel="noopener noreferrer" />}
            >
              Open the site
            </Button>
          </div>
        </div>
      )}

      {!loading && data && data.signups.length === 0 && (
        <p className="text-muted-foreground text-sm">
          Nobody has joined yet. You can be the first, over on the site.
        </p>
      )}

      {!loading && data && data.signups.length > 0 && (
        <ul className="grid grid-cols-3 gap-x-4 gap-y-6 sm:grid-cols-6 md:grid-cols-8">
          {data.signups.map((person) => (
            <li key={person.id} className="flex flex-col items-center text-center">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={avatarUrl(person.seed, person.gender)}
                alt=""
                width={56}
                height={56}
                loading="lazy"
                className="bg-background size-14 rounded-full border"
              />
              <span className="mt-2 w-full truncate text-xs font-medium">{person.name}</span>
              <span className="text-muted-foreground w-full truncate text-[11px]">
                {person.country}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
