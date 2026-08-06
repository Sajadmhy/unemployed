import { db } from "@/lib/db";
import { CORS, corsOptions } from "@/lib/cors";
import { ipHash, isUniqueViolation } from "@/lib/ip";

export const dynamic = "force-dynamic";

// Past this many unique-IP flags, a post stops showing on the board. Reviewed
// and unhidden (or left hidden) manually via the Neon SQL console.
const HIDE_THRESHOLD = 3;

export async function OPTIONS() {
  return corsOptions();
}

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return fail("generic", 400);
  }
  if (typeof body !== "object" || body === null) return fail("generic", 400);

  const { experienceId } = body as Record<string, unknown>;
  const id = Number(experienceId);
  if (!Number.isInteger(id) || id <= 0) return fail("generic", 400);

  try {
    const sql = db();
    await sql`insert into experience_flags (experience_id, ip_hash) values (${id}, ${ipHash(request)})`;

    await sql`
      update experiences
      set flag_count = flag_count + 1,
          hidden = (flag_count + 1 >= ${HIDE_THRESHOLD})
      where id = ${id}
    `;

    return Response.json({ ok: true }, { status: 200, headers: CORS });
  } catch (error) {
    // Already flagged by this browser. Treat it as success rather than error.
    if (isUniqueViolation(error)) {
      return Response.json({ ok: true }, { status: 200, headers: CORS });
    }
    console.error("flag failed", error);
    return fail("generic", 503);
  }
}

function fail(error: string, status: number) {
  return Response.json({ error }, { status, headers: CORS });
}
