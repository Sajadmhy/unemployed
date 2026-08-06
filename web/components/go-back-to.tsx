"use client";

import { useEffect, useState } from "react";

/**
 * What to do with the next few minutes, since the answer is "not watch this".
 *
 * Every slow thing in this app is a local model thinking on your own CPU, so
 * the wait is real and there is no server to blame or upgrade. Saying "this
 * takes a while" and then showing a bar that barely moves reads as broken. A
 * line that keeps changing proves the page is alive, and telling someone to go
 * away is the honest advice: the run finishes whether or not it is watched.
 *
 * "Go back to" stays put and only the tail rotates, so the eye has one word to
 * track instead of a whole line reflowing every few seconds.
 */
const THINGS = [
  "solving DSA",
  "building that side project",
  "doomscrolling",
  "your 47 open tabs",
  "the LeetCode daily",
  "pretending to read the docs",
  "making chai",
  "that portfolio you started in March",
];

const EVERY_MS = 2800;

export function GoBackTo({ className = "" }: { className?: string }) {
  const [i, setI] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setI((n) => (n + 1) % THINGS.length), EVERY_MS);
    return () => clearInterval(timer);
  }, []);

  return (
    <p className={`text-xs text-muted-foreground ${className}`}>
      Go back to{" "}
      {/* `key` is the point: changing it remounts the span, which restarts the
          entrance animation. Without it React reuses the node, the text swaps
          and nothing moves. */}
      <span key={i} className="quip inline-block font-medium text-foreground/70">
        {THINGS[i]}
      </span>
    </p>
  );
}
