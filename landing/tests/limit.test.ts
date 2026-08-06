import assert from "node:assert/strict";
import { test } from "node:test";

import { readLimit } from "../lib/limit.ts";

const opts = { fallback: 100, max: 200 };
const params = (query: string) => new URLSearchParams(query);

test("a missing limit falls back rather than becoming 1", () => {
  // The regression this file exists for. `Number(null)` is 0 and 0 is finite,
  // so the obvious implementation treated "no limit given" as a valid number
  // and clamped it to the minimum. Every caller that omitted the parameter got
  // exactly one row back, which looked like an empty board rather than a bug.
  assert.equal(readLimit(params(""), opts), 100);
});

test("an empty limit falls back too", () => {
  assert.equal(readLimit(params("limit="), opts), 100);
  assert.equal(readLimit(params("limit=%20"), opts), 100);
});

test("a valid limit is used", () => {
  assert.equal(readLimit(params("limit=25"), opts), 25);
});

test("limits are clamped to the range", () => {
  assert.equal(readLimit(params("limit=0"), opts), 1);
  assert.equal(readLimit(params("limit=-5"), opts), 1);
  assert.equal(readLimit(params("limit=9999"), opts), 200);
});

test("a fractional limit is truncated", () => {
  assert.equal(readLimit(params("limit=10.9"), opts), 10);
});

test("nonsense falls back instead of throwing", () => {
  assert.equal(readLimit(params("limit=abc"), opts), 100);
  assert.equal(readLimit(params("limit=NaN"), opts), 100);
  assert.equal(readLimit(params("limit=Infinity"), opts), 100);
});
