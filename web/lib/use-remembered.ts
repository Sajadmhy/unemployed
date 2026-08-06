"use client";

import { useEffect, useState } from "react";

/**
 * A boolean that survives a reload, for view toggles like "hide completed".
 *
 * The stored value is read *after* mount rather than during render: the server
 * has no localStorage, so reading it while rendering would produce different
 * markup on the two sides and a hydration error. One frame of the default is
 * the price of that correctness.
 */
export function useRemembered(key: string, fallback: boolean) {
  const [value, setValue] = useState(fallback);

  useEffect(() => {
    const stored = localStorage.getItem(key);
    if (stored !== null) setValue(stored === "true");
  }, [key]);

  function update(next: boolean) {
    setValue(next);
    localStorage.setItem(key, String(next));
  }

  return [value, update] as const;
}
