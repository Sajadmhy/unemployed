/**
 * Applies content/schema.sql to whatever DATABASE_URL points at.
 *
 * Idempotent (every statement is `if not exists`), so running it twice is safe.
 * This exists instead of a migration tool because there is exactly one table.
 */
import { readFileSync } from "node:fs";
import { neon } from "@neondatabase/serverless";

const url = process.env.DATABASE_URL;
if (!url) {
  console.error("DATABASE_URL is not set. Copy .env.example to .env.local first.");
  process.exit(1);
}

const sql = neon(url);
const schema = readFileSync(new URL("../content/schema.sql", import.meta.url), "utf8");

// Comments come out before the split, not after. A semicolon inside a `--`
// comment is invisible to a reader and splits a statement in half for this
// script, which then fails with "syntax error at end of input" pointing at a
// character offset rather than at the comment that caused it. Stripping first
// makes the split see only real statement terminators.
//
// This assumes no `--` appears inside a string literal, which is true here and
// is why the schema is one file that a person reads before running.
const statements = schema
  .replace(/--[^\n]*/g, "")
  .split(";")
  .map((s) => s.trim())
  .filter(Boolean);

for (const statement of statements) {
  await sql.query(statement);
  console.log("ok:", statement.split("\n")[0].slice(0, 70));
}

const [{ count }] = await sql`select count(*)::int as count from signups`;
console.log(`\nschema applied. signups table holds ${count} row(s).`);
