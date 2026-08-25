import test from "node:test";
import assert from "node:assert/strict";
import { extractDois } from "../dist/services/parsers.js";

test("finds a plain DOI in text", () => {
  const text = "See https://doi.org/10.1016/S0140-6736(97)11096-0 for details.";
  assert.deepEqual(extractDois(text), ["10.1016/S0140-6736(97)11096-0"]);
});

test("finds multiple DOIs and deduplicates, preserving order", () => {
  const text = "First 10.1000/abc then 10.1000/def then 10.1000/abc again.";
  assert.deepEqual(extractDois(text), ["10.1000/abc", "10.1000/def"]);
});

test("strips trailing sentence punctuation", () => {
  const text = "This paper (see 10.1000/abc) is good. Also 10.1000/def.";
  const dois = extractDois(text);
  assert.ok(dois.includes("10.1000/abc"));
  assert.ok(dois.includes("10.1000/def"));
  assert.ok(!dois.some((d) => d.endsWith(")") || d.endsWith(".")));
});

test("returns an empty array for text with no DOIs", () => {
  assert.deepEqual(extractDois("Just some ordinary prose with no citations."), []);
});

test("handles a DOI with parentheses in the suffix without truncating it", () => {
  const text = "10.1016/S0140-6736(97)11096-0";
  assert.deepEqual(extractDois(text), ["10.1016/S0140-6736(97)11096-0"]);
});
