import { auth } from "@/auth";
import { db, recentExperiences, signupForGoogleSub } from "@/lib/db";
import {
  checkCompany,
  checkRole,
  checkText,
  isValidResult,
  isValidRoundOutcome,
  isValidRoundType,
} from "@/lib/validate";
import { CACHE, CORS, corsOptions } from "@/lib/cors";
import { ipHash } from "@/lib/ip";
import { readLimit } from "@/lib/limit";

// Same reasoning as app/api/signups/route.ts: request-time data, never
// prerendered.
export const dynamic = "force-dynamic";

const MAX_PER_IP = 5;
const WINDOW_MINUTES = 60;
const MAX_ROUNDS = 20;

export async function OPTIONS() {
  return corsOptions();
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const company = searchParams.get("company")?.trim() || undefined;
  // Ids are bigints, so only digits can be one. Anything else is dropped rather
  // than handed to Postgres to reject.
  const rawSignup = searchParams.get("signupId")?.trim();
  const signupId = rawSignup && /^\d+$/.test(rawSignup) ? rawSignup : undefined;
  const limit = readLimit(searchParams, { fallback: 100, max: 200 });

  try {
    const experiences = await recentExperiences({ company, signupId, limit });
    return Response.json(
      { count: experiences.length, experiences },
      { headers: { ...CORS, ...CACHE } },
    );
  } catch (error) {
    console.error("experiences read failed", error);
    return Response.json({ error: "board unavailable" }, { status: 503, headers: CORS });
  }
}

type RoundInput = {
  round_number: number;
  round_type: string;
  description: string;
  outcome: string;
};

export async function POST(request: Request) {
  // Same rule as signups: the poster is whoever the session cookie says, not
  // whoever the request body claims.
  const session = await auth();
  const googleSub = session?.user?.id;
  if (!googleSub) return fail("mustSignIn", 401);

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return fail("generic", 400);
  }
  if (typeof body !== "object" || body === null) return fail("generic", 400);

  const { company: rawCompany, role: rawRole, result, summary: rawSummary, rounds } =
    body as Record<string, unknown>;

  const { company, problem: companyProblem } = checkCompany(rawCompany);
  if (companyProblem) return fail(companyProblem, 400, "company");

  const { role, problem: roleProblem } = checkRole(rawRole);
  if (roleProblem) return fail(roleProblem, 400, "role");

  if (!isValidResult(result)) return fail("generic", 400, "result");

  const { text: summary, problem: summaryProblem } = checkText(rawSummary, 2000);
  if (summaryProblem) return fail(summaryProblem, 400, "summary");

  const roundsCheck = checkRounds(rounds);
  if (roundsCheck.problem) return fail(roundsCheck.problem, 400, "rounds");

  try {
    // Signed in but never finished a profile: there is no row to attach this
    // to, and no name or face to show it under.
    const signup = await signupForGoogleSub(googleSub);
    if (!signup) return fail("mustJoinWall", 403);
    const signupId = signup.id;

    const sql = db();

    // Rate limit lives inside the same statement as the insert, same trick as
    // signups: it holds across serverless instances with no extra round trip.
    // Header + rounds insert in one statement via jsonb_to_recordset, since
    // the HTTP transaction API can't feed one insert's id into the next.
    const rows = (await sql`
      with recent as (
        select count(*)::int as n from experiences
        where ip_hash = ${ipHash(request)}
          and created_at > now() - make_interval(mins => ${WINDOW_MINUTES})
      ), inserted as (
        insert into experiences (signup_id, company, role, result, summary, ip_hash)
        select ${signupId}, ${company}, ${role}, ${result}, ${summary}, ${ipHash(request)}
        from recent where n < ${MAX_PER_IP}
        returning id
      ), rounds_inserted as (
        insert into experience_rounds (experience_id, round_number, round_type, description, outcome)
        select (select id from inserted), r.round_number, r.round_type, r.description, r.outcome
        from jsonb_to_recordset(${JSON.stringify(roundsCheck.rounds)}::jsonb)
          as r(round_number int, round_type text, description text, outcome text)
        where exists (select 1 from inserted)
        returning experience_id
      )
      select inserted.id, s.id as signup_id, s.name, s.seed, s.gender
      from inserted
      join signups s on s.id = ${signupId}
    `) as { id: string; signup_id: string; name: string; seed: string; gender: string }[];

    if (rows.length === 0) return fail("rateLimited", 429);
    return Response.json(rows[0], { status: 201, headers: CORS });
  } catch (error) {
    console.error("experience post failed", error);
    return fail("generic", 503);
  }
}

function checkRounds(raw: unknown): { rounds: RoundInput[]; problem: string | null } {
  if (!Array.isArray(raw) || raw.length === 0 || raw.length > MAX_ROUNDS) {
    return { rounds: [], problem: "rounds" };
  }

  const rounds: RoundInput[] = [];
  for (let i = 0; i < raw.length; i++) {
    const entry = raw[i];
    if (typeof entry !== "object" || entry === null) return { rounds: [], problem: "rounds" };
    const { round_type, description, outcome } = entry as Record<string, unknown>;

    if (!isValidRoundType(round_type)) return { rounds: [], problem: "rounds" };
    if (!isValidRoundOutcome(outcome)) return { rounds: [], problem: "rounds" };

    const { text, problem } = checkText(description, 1000);
    if (problem) return { rounds: [], problem: "rounds" };

    rounds.push({ round_number: i + 1, round_type, description: text, outcome });
  }

  return { rounds, problem: null };
}

function fail(error: string, status: number, field?: string) {
  return Response.json({ error, field }, { status, headers: CORS });
}
