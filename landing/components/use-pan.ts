"use client";

import { useEffect, useRef } from "react";

/**
 * Grab a scrolling surface and drag it around.
 *
 * Only the mouse is handled. Touch and pen already drag a scroll container,
 * with momentum and rubber banding that reimplementing would only make worse,
 * so those pointers are left to the browser.
 *
 * The listeners move to the window for the duration of a drag rather than using
 * pointer capture, because capture retargets the click that follows and the
 * faces on the wall are buttons that have to keep working.
 */
export function usePan<T extends HTMLElement>() {
  const ref = useRef<T>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let active = false;
    let moved = false;
    let startX = 0;
    let startY = 0;
    let fromLeft = 0;
    let fromTop = 0;

    const move = (event: PointerEvent) => {
      const dx = event.clientX - startX;
      const dy = event.clientY - startY;
      // A few pixels of wobble while clicking is not a drag.
      if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
      el.scrollLeft = fromLeft - dx;
      el.scrollTop = fromTop - dy;
    };

    const stop = () => {
      if (!active) return;
      active = false;
      delete el.dataset.panning;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
      window.removeEventListener("pointercancel", stop);
    };

    const down = (event: PointerEvent) => {
      if (event.pointerType !== "mouse" || event.button !== 0) return;
      active = true;
      moved = false;
      startX = event.clientX;
      startY = event.clientY;
      fromLeft = el.scrollLeft;
      fromTop = el.scrollTop;
      el.dataset.panning = "true";
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", stop);
      window.addEventListener("pointercancel", stop);
    };

    // Dragging across the wall must not also open whichever face you let go on.
    // Swallowed on the way down, so it never reaches the button.
    const click = (event: MouseEvent) => {
      if (!moved) return;
      moved = false;
      event.preventDefault();
      event.stopPropagation();
    };

    // Without this the browser starts its own image drag and the pan stops dead
    // on the first face the cursor crosses.
    const dragstart = (event: Event) => event.preventDefault();

    el.addEventListener("pointerdown", down);
    el.addEventListener("click", click, true);
    el.addEventListener("dragstart", dragstart);

    return () => {
      stop();
      el.removeEventListener("pointerdown", down);
      el.removeEventListener("click", click, true);
      el.removeEventListener("dragstart", dragstart);
    };
  }, []);

  return ref;
}
