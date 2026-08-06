/**
 * The gender mapping is a list of 47 hand-copied variant names. A typo in one of
 * them is the whole risk here, so the first test checks every name against the
 * style definition itself rather than trusting the list.
 *
 * `lib/avatar.ts` is not imported: it starts with `import "server-only"`, which
 * throws outside a React server environment. What matters is tested anyway, since
 * that module is a cache around exactly the call made below.
 */
import { strict as assert } from "node:assert";
import { test } from "node:test";

import { Avatar, Style } from "@dicebear/core";
import definition from "@dicebear/styles/open-peeps.json" with { type: "json" };

import { GENDER_OPTIONS, GENDERS, asGender } from "../lib/gender-options.ts";

const style = new Style(definition as never);
const render = (seed: string, gender: "female" | "male" | "neutral") =>
  new Avatar(style, { seed, ...GENDER_OPTIONS[gender] }).toString();

test("every hairstyle named in the gender lists exists in the style", () => {
  const real = new Set(
    Object.keys((definition as never as Record<string, never>)["components"]["head"]["variants"]),
  );
  for (const gender of ["female", "male"] as const) {
    const named = GENDER_OPTIONS[gender].headVariant as string[];
    assert.ok(named.length > 0, `${gender} should constrain the hairstyle pool`);
    for (const variant of named) {
      assert.ok(real.has(variant), `${gender} names "${variant}", which the style does not have`);
    }
  }
});

test("the two gendered pools do not overlap", () => {
  const female = new Set(GENDER_OPTIONS.female.headVariant as string[]);
  const shared = (GENDER_OPTIONS.male.headVariant as string[]).filter((v) => female.has(v));
  assert.deepEqual(shared, [], "a hairstyle in both pools makes the choice meaningless");
});

test("rendering produces an svg", () => {
  assert.ok(render("seed-one", "neutral").startsWith("<svg"));
});

test("the same seed always draws the same face", () => {
  assert.equal(render("stable", "female"), render("stable", "female"));
});

test("gender changes the face for one seed", () => {
  const seed = "same-seed";
  assert.notEqual(render(seed, "female"), render(seed, "male"));
  assert.notEqual(render(seed, "female"), render(seed, "neutral"));
});

test("women never get facial hair", () => {
  assert.equal(GENDER_OPTIONS.female.facialHairProbability, 0);
});

test("an unknown gender falls back to neutral rather than throwing", () => {
  assert.equal(asGender("attack-helicopter"), "neutral");
  assert.equal(asGender(null), "neutral");
  assert.equal(asGender("female"), "female");
  assert.deepEqual([...GENDERS], ["female", "male", "neutral"]);
});
