"use client";

/**
 * The wordmark: un̶employed, with the "un" struck out.
 *
 * The joke has to land in one glance, so the strike is not a text decoration —
 * it is a line that draws itself across the "un" while those two letters fade
 * back, which is the moment the word changes meaning. Everything else in this
 * app is deliberately plain, so this is the one place with motion.
 *
 * Monospace and lowercase because the thing you are looking at is a local tool
 * you run yourself, and the caret says the same.
 *
 * `group-hover` replays the animation on the nav mark; `prefers-reduced-motion`
 * skips straight to the struck-through end state.
 */
export function Logo({ size = "nav" }: { size?: "nav" | "hero" }) {
  const hero = size === "hero";

  return (
    <span
      className={`logo group inline-flex select-none items-baseline font-mono tracking-tight ${
        hero ? "logo--hero text-5xl sm:text-7xl" : "text-base"
      }`}
      aria-label="unemployed"
      role="img"
    >
      <span className="logo__struck relative text-muted-foreground">
        un
        <span className="logo__strike" aria-hidden />
      </span>
      <span className="font-semibold text-foreground">employed</span>
      <span className="logo__caret ml-0.5 text-foreground" aria-hidden>
        _
      </span>
    </span>
  );
}
