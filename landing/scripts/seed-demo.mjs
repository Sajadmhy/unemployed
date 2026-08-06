/**
 * Fills the wall with throwaway rows so the hero crowd can be looked at during
 * design work. Not for production: `npm run seed:clear` removes exactly these
 * rows, which are the ones whose ip_hash is 'seed-demo'.
 */
import { neon } from "@neondatabase/serverless";

const sql = neon(process.env.DATABASE_URL);

if (process.argv.includes("--clear")) {
  await sql`delete from experiences where ip_hash = 'seed-demo'`;
  await sql`delete from signups where ip_hash = 'seed-demo'`;
  const [{ c }] = await sql`select count(*)::int as c from signups`;
  console.log(`demo rows removed. ${c} real row(s) left.`);
  process.exit(0);
}

const people = [
  ["Aarav", "IN", "male"], ["Priya", "IN", "female"], ["Rohan", "IN", "male"],
  ["Sneha", "IN", "female"], ["Kabir", "IN", "male"], ["Ananya", "IN", "female"],
  ["Wei", "SG", "male"], ["Mariam", "AE", "female"], ["Diego", "MX", "male"],
  ["Lena", "DE", "female"], ["Tom", "GB", "male"], ["Yuki", "JP", "female"],
  ["Sam", "US", "neutral"], ["Fatima", "PK", "female"], ["Arjun", "IN", "male"],
  ["Chloe", "CA", "female"], ["Ravi", "IN", "male"], ["Zara", "GB", "female"],
  ["Ibrahim", "NG", "male"], ["Mei", "TW", "female"], ["Luca", "IT", "male"],
  ["Nadia", "EG", "female"], ["Karan", "IN", "male"], ["Ella", "AU", "female"],
];

for (const [name, country, gender] of people) {
  const seed = Math.random().toString(36).slice(2, 10);
  await sql`
    insert into signups (name, country, gender, seed, ip_hash, client_id)
    values (${name}, ${country}, ${gender}, ${seed}, 'seed-demo', ${"demo-" + name})
    -- The unique index is partial, so its predicate has to be repeated here
    -- for Postgres to match it.
    on conflict (client_id) where client_id is not null do nothing
  `;
}

const [{ c }] = await sql`select count(*)::int as c from signups`;
console.log(`seeded. ${c} row(s) total.`);

// A handful of interview experiences, tied to the demo signups above so the
// experiences page has something to look at too. Cleared first so reruns
// don't pile up duplicates the way the signups upsert already avoids.
await sql`delete from experiences where ip_hash = 'seed-demo'`;

const experiences = [
  {
    signupName: "Aarav",
    company: "Freshworks",
    role: "SDE 1",
    result: "offer",
    summary: "Two rounds, straightforward once you know the basics.",
    rounds: [
      { round_type: "oa", description: "Arrays and strings, easy to medium.", outcome: "cleared" },
      { round_type: "technical", description: "System design lite: design a URL shortener.", outcome: "cleared" },
    ],
  },
  {
    signupName: "Priya",
    company: "Zomato",
    role: "Backend Intern",
    result: "rejected",
    summary: "Rejected after the technical round.",
    rounds: [
      { round_type: "technical", description: "Asked to design a rate limiter.", outcome: "rejected" },
    ],
  },
  {
    signupName: "Rohan",
    company: "Freshworks",
    role: "SDE 2",
    result: "pending",
    summary: "Waiting to hear back after the managerial round.",
    rounds: [
      { round_type: "oa", description: "Two DSA problems, medium difficulty.", outcome: "cleared" },
      { round_type: "technical", description: "Deep dive on a past project.", outcome: "cleared" },
      { round_type: "managerial", description: "Behavioral and team-fit questions.", outcome: "pending" },
    ],
  },
];

for (const exp of experiences) {
  const [signup] = await sql`
    select id from signups where name = ${exp.signupName} and ip_hash = 'seed-demo' limit 1
  `;
  if (!signup) continue;

  const [{ id: experienceId }] = await sql`
    insert into experiences (signup_id, company, role, result, summary, ip_hash)
    values (${signup.id}, ${exp.company}, ${exp.role}, ${exp.result}, ${exp.summary}, 'seed-demo')
    returning id
  `;

  for (let i = 0; i < exp.rounds.length; i++) {
    const round = exp.rounds[i];
    await sql`
      insert into experience_rounds (experience_id, round_number, round_type, description, outcome)
      values (${experienceId}, ${i + 1}, ${round.round_type}, ${round.description}, ${round.outcome})
    `;
  }
}

const [{ e }] = await sql`select count(*)::int as e from experiences`;
console.log(`seeded. ${e} experience(s) total.`);
