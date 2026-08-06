"use client";

import { useEffect, useRef } from "react";

/**
 * A dialog, built on the platform's own `<dialog>` element.
 *
 * Using the real element rather than a div with a high z-index gets the
 * behaviour people expect for free and correctly: focus is trapped inside it,
 * the rest of the page becomes inert to screen readers, and it paints in the
 * top layer so no stacking context can end up above it.
 *
 * Two things about the wiring are deliberate.
 *
 * The sync effect has no dependency array, so it runs after every render and
 * reconciles the element against the `open` prop each time. That makes a
 * desync self-healing rather than permanent. The first version only ran when
 * `open` changed and treated the element's `close` event as the single source
 * of truth for "it got closed" - and when that event does not arrive, React
 * still believes the dialog is open, so the next open is a no-op and the
 * dialog never comes back. Reconciling every render cannot get stuck that way.
 *
 * And every route out of the dialog calls `onClose` directly instead of going
 * through the element and waiting to hear about it. Escape is intercepted at
 * `cancel`, where preventDefault stops the browser closing it behind React's
 * back, leaving React the only thing that decides whether it is open.
 */
export function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    // showModal() throws if it is already open, and close() does nothing useful
    // if it isn't, so both are guarded on the element's own state.
    if (open && !dialog.open) dialog.showModal();
    else if (!open && dialog.open) dialog.close();
  });

  return (
    <dialog
      ref={ref}
      aria-label={title}
      onCancel={(event) => {
        // Escape. Let React close it so state and the DOM agree.
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        // The dialog's box covers the viewport, so a click landing on the
        // element itself is a click on the backdrop. Anything inside the panel
        // below stops before it reaches here.
        if (event.target === ref.current) onClose();
      }}
      className="m-auto w-[min(44rem,calc(100vw-2rem))] rounded-xl border bg-background p-0 text-foreground backdrop:bg-black/50 backdrop:backdrop-blur-sm"
    >
      <div className="flex items-start justify-between gap-4 border-b px-6 py-4">
        <h2 className="font-serif text-xl leading-tight">{title}</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="text-muted-foreground hover:text-foreground -mr-1 rounded-sm px-2 text-xl leading-none focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
        >
          &times;
        </button>
      </div>
      <div className="max-h-[70svh] overflow-y-auto px-6 py-5">{children}</div>
    </dialog>
  );
}
