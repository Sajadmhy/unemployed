import { redirect } from "next/navigation";

/** The ranked list lives at /today now — this keeps old links working. */
export default function MatchesRedirect() {
  redirect("/today");
}
