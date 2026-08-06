"use client";

import { useEffect } from "react";

/** Pixels per second. Slow enough to read as drifting rather than sliding past. */
const SPEED = 32;

/**
 * Carry a scrolling surface sideways on its own, forever.
 *
 * The loop is seamless rather than a jump back to the start. The caller repeats
 * the opening run of faces at the end and marks the first of them; when the
 * surface has travelled the width of the original run it is moved back by
 * exactly that much, which leaves the same faces under the same pixels. Until
 * everything has loaded there is no marker and so no wrap, which is right:
 * a crowd that is still growing has no end to come back from.
 *
 * It gives way to the reader rather than competing with them. Hovering a face
 * stops it, because the reason to hover is to read a name off it, and dragging
 * stops it because two things moving one surface is a fight the reader loses.
 */
export function useDrift(ref: React.RefObject<HTMLElement | null>, count: number) {
  useEffect(() => {
    const el = ref.current;
    if (!el || count === 0) return;
    // Motion with no purpose but motion is exactly what this setting turns off.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    // Delegated, so hovering does not cost a render per face. Moving between an
    // avatar and its name label leaves one element and enters another inside
    // the same face; that reads as a single frame of not hovering, which is
    // shorter than anyone can see.
    let over = false;
    const enter = (event: PointerEvent) => {
      if ((event.target as Element).closest?.(".hero-board__face")) over = true;
    };
    const leave = (event: PointerEvent) => {
      if ((event.target as Element).closest?.(".hero-board__face")) over = false;
    };
    el.addEventListener("pointerover", enter);
    el.addEventListener("pointerout", leave);

    // How far it travels before it can start again. Measured rather than
    // worked out, because the row count and the face size both come from CSS
    // and both change with the viewport.
    let run = 0;
    const measure = () => {
      const from = el.querySelector<HTMLElement>("[data-loop-from]");
      const repeat = el.querySelector<HTMLElement>("[data-loop]");
      run = from && repeat ? repeat.offsetLeft - from.offsetLeft : 0;
    };
    measure();
    window.addEventListener("resize", measure);

    // Kept as a float of its own. Reading the position back out of the element
    // every frame would round away a third of a pixel each time, which at this
    // speed is most of the movement.
    let position = el.scrollLeft;
    let previous = 0;

    let frame = requestAnimationFrame(function step(now: number) {
      frame = requestAnimationFrame(step);
      // A tab returning from the background reports one enormous gap, which
      // would fling the crowd sideways on the frame you looked back at it.
      const elapsed = previous ? Math.min(now - previous, 100) : 0;
      previous = now;

      if (over || el.dataset.panning) {
        position = el.scrollLeft;
        return;
      }
      // A drag, or an arrow key, wins. Follow it instead of pulling against it.
      if (Math.abs(el.scrollLeft - position) > 2) position = el.scrollLeft;

      position += (elapsed / 1000) * SPEED;
      if (run > 0 && position >= run) position -= run;
      el.scrollLeft = position;
    });

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", measure);
      el.removeEventListener("pointerover", enter);
      el.removeEventListener("pointerout", leave);
    };
    // Re-measured whenever a page of people lands, since that is what moves the
    // marker, and when the repeat first appears.
  }, [ref, count]);
}
