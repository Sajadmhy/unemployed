"use client";

import { createContext, useCallback, useContext, useState } from "react";

import type { SignupRow } from "@/lib/db";

type PeopleState = {
  /** Joined during this visit. Kept apart from the server's list so the page
   *  can still stream the crowd in without waiting for the client. */
  added: SignupRow[];
  joined: boolean;
  add: (row: SignupRow) => void;
};

const PeopleContext = createContext<PeopleState>({
  added: [],
  joined: false,
  add: () => {},
});

export const usePeople = () => useContext(PeopleContext);

/**
 * Holds the one piece of state the whole page shares: are you on the wall, and
 * who arrived while you were looking at it.
 *
 * `joined` is passed in from the server, which knows the answer because it
 * knows the session. It used to be read from localStorage, which was a guess
 * about a different browser's history and could disagree with the database in
 * both directions - a cleared browser hid a real profile, and a leftover key
 * offered a post button to someone with no row to post as.
 */
export function PeopleProvider({
  joined: joinedOnServer = false,
  children,
}: {
  joined?: boolean;
  children: React.ReactNode;
}) {
  const [added, setAdded] = useState<SignupRow[]>([]);

  const add = useCallback((row: SignupRow) => {
    setAdded((prev) => (prev.some((p) => p.id === row.id) ? prev : [row, ...prev]));
  }, []);

  return (
    <PeopleContext value={{ added, joined: joinedOnServer || added.length > 0, add }}>
      {children}
    </PeopleContext>
  );
}
