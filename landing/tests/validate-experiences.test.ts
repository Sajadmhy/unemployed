/**
 * The experience wall's free-text fields go through the same cleaning and
 * profanity checks as a name (see validate.test.ts), so this file only covers
 * what's new: the enum guards and the shared checkText helper.
 */
import { strict as assert } from "node:assert";
import { test } from "node:test";

import {
  checkCompany,
  checkRole,
  checkText,
  isValidResult,
  isValidRoundOutcome,
  isValidRoundType,
  ROUND_OUTCOMES,
  ROUND_TYPES,
  RESULTS,
} from "../lib/validate.ts";

test("checkText rejects empty, too long and profane the same way checkName does", () => {
  assert.equal(checkText("", 100).problem, "empty");
  assert.equal(checkText("a".repeat(101), 100).problem, "tooLong");
  assert.equal(checkText("a".repeat(100), 100).problem, null);
  assert.equal(checkText("fuck", 100).problem, "profane");
});

test("checkCompany and checkRole cap at 80 characters", () => {
  assert.equal(checkCompany("Freshworks").problem, null);
  assert.equal(checkCompany("a".repeat(81)).problem, "tooLong");
  assert.equal(checkRole("SDE 1").problem, null);
  assert.equal(checkRole("a".repeat(81)).problem, "tooLong");
});

test("result is an allowlist", () => {
  for (const r of RESULTS) assert.ok(isValidResult(r));
  assert.ok(!isValidResult("accepted"));
  assert.ok(!isValidResult(undefined));
});

test("round type is an allowlist", () => {
  for (const t of ROUND_TYPES) assert.ok(isValidRoundType(t));
  assert.ok(!isValidRoundType("aptitude"));
});

test("round outcome is an allowlist", () => {
  for (const o of ROUND_OUTCOMES) assert.ok(isValidRoundOutcome(o));
  assert.ok(!isValidRoundOutcome("maybe"));
});
