import Link from "next/link";

import { PageNav } from "@/components/page-nav";
import { copy } from "@/lib/copy";

/**
 * Where Auth.js sends anyone whose sign in did not complete.
 *
 * It exists because the built in page for this says "there is a problem with
 * the server configuration", which sends people away believing the site is
 * broken. It almost never is. The errors behind it are `MissingCSRF` and
 * `InvalidCheck`, which both mean one of the two cookies the OAuth round trip
 * needs was not there on the way back: an in app browser dropped it, the tab
 * sat long enough for the fifteen minute verifier to expire, or the callback
 * was replayed with the back button after its cookie had been spent.
 *
 * All three are fixed by starting again, so that is the one thing on the page.
 *
 * It reads nothing. No session, no database, no viewer lookup. This is the page
 * people land on when something has already gone wrong, and a page that can
 * fail in its own right is worse than the message it replaced.
 */
export default async function AuthErrorPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;

  // The one case that is not a lost cookie: they said no on Google's screen.
  // Telling that person their browser misbehaved would be a lie they can see
  // through, so it gets its own wording.
  const denied = error === "AccessDenied";

  return (
    <>
      <PageNav />
      <main id="top" className="px-6 pt-28 pb-32 md:px-12 lg:px-24">
        <div className="mx-auto w-full max-w-3xl">
          <p className="text-muted-foreground font-mono text-[11px] tracking-[0.2em] uppercase">
            {copy.join.label}
          </p>
          <h1 className="mt-5 font-serif text-3xl leading-tight sm:text-4xl">
            {denied ? copy.auth.errorDeniedHeading : copy.auth.errorHeading}
          </h1>
          <p className="text-muted-foreground mt-4 text-base leading-relaxed">
            {denied ? copy.auth.errorDeniedBody : copy.auth.errorBody}
          </p>

          <Link href="/join" className="btn-solid mt-8 inline-flex">
            {copy.auth.errorRetry}
          </Link>

          {/* Only worth saying when a cookie is the likely culprit. Someone who
              cancelled on purpose does not need troubleshooting. */}
          {!denied && (
            <div className="text-muted-foreground mt-10 space-y-3 border-t pt-6 text-sm leading-relaxed">
              <p>{copy.auth.errorInApp}</p>
              <p>{copy.auth.errorStale}</p>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
