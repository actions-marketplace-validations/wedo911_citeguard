import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { analyzeWork } from "../dist/services/analyze.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURES = path.join(__dirname, "fixtures");

function loadFixture(name) {
  const payload = JSON.parse(readFileSync(path.join(FIXTURES, name), "utf-8"));
  return payload.message;
}

test("Wakefield 1998 is retracted via the updated-by/retraction-watch signal", () => {
  const message = loadFixture("wakefield_1998.json");
  const result = analyzeWork(message);

  assert.equal(result.verdict, "retracted");
  const retraction = result.signals.find((s) => s.type === "retraction");
  assert.ok(retraction);
  assert.equal(retraction.source, "retraction-watch");
  assert.equal(retraction.date, "2010-02-06");

  const correction = result.signals.find((s) => s.type === "correction");
  assert.ok(correction);
  assert.equal(correction.date, "2004-03-06");
});

test("Wakefield title carries the RETRACTED prefix too", () => {
  const message = loadFixture("wakefield_1998.json");
  const result = analyzeWork(message);
  assert.ok(result.title.toUpperCase().startsWith("RETRACTED:"));
});

test("Surgisphere Lancet paper is retracted via the publisher update-to signal", () => {
  const message = loadFixture("surgisphere_mehra_2020.json");
  const result = analyzeWork(message);

  assert.equal(result.verdict, "retracted");
  const retraction = result.signals.find((s) => s.type === "retraction");
  assert.ok(retraction);
  assert.equal(retraction.source, "publisher");
  assert.ok(retraction.noticeDoi);
});

test("Watson & Crick 1953 is clean -- no false positive", () => {
  const message = loadFixture("watson_crick_1953_clean.json");
  const result = analyzeWork(message);

  assert.equal(result.verdict, "clean");
  assert.deepEqual(result.signals, []);
  assert.match(result.title.toLowerCase(), /nucleic acid/);
});

// -- synthetic cases mirroring the Python test suite ----------------------------

test("expression of concern via update-to maps to concern, not retracted", () => {
  const message = {
    DOI: "10.9999/example",
    title: ["A perfectly normal-sounding title"],
    "update-to": [{ DOI: "10.9999/notice", type: "expression_of_concern", label: "Expression of Concern", source: "publisher", updated: { "date-parts": [[2023, 5, 1]] } }],
  };
  assert.equal(analyzeWork(message).verdict, "concern");
});

test("correction only maps to corrected, not treated as problematic-critical", () => {
  const message = {
    DOI: "10.9999/example",
    title: ["A perfectly normal-sounding title"],
    "update-to": [{ DOI: "10.9999/notice", type: "correction", label: "Correction", source: "publisher" }],
  };
  assert.equal(analyzeWork(message).verdict, "corrected");
});

test("title heuristic 'Expression of Concern:' is not upgraded to retracted", () => {
  const message = { DOI: "10.9999/example", title: ["Expression of Concern: Some paper"] };
  assert.equal(analyzeWork(message).verdict, "concern");
});

test("title heuristic 'Corrigendum:' maps to corrected, not retracted", () => {
  const message = { DOI: "10.9999/example", title: ["Corrigendum: Some paper"] };
  assert.equal(analyzeWork(message).verdict, "corrected");
});

test("title heuristic 'WITHDRAWN:' maps to retracted", () => {
  const message = { DOI: "10.9999/example", title: ["WITHDRAWN: Some paper"] };
  assert.equal(analyzeWork(message).verdict, "retracted");
});

test("structured signals take precedence over the title heuristic", () => {
  const message = {
    DOI: "10.9999/example",
    title: ["RETRACTED: Some paper"],
    "update-to": [{ DOI: "10.9999/notice", type: "correction", label: "Correction", source: "publisher" }],
  };
  const result = analyzeWork(message);
  assert.equal(result.verdict, "corrected");
  assert.ok(result.signals.every((s) => s.source !== "title_prefix"));
});

test("unrelated update type is ignored", () => {
  const message = {
    DOI: "10.9999/example",
    title: ["A perfectly normal-sounding title"],
    "update-to": [{ DOI: "10.9999/notice", type: "new_version", label: "New Version", source: "publisher" }],
  };
  assert.equal(analyzeWork(message).verdict, "clean");
});

test("missing title does not throw", () => {
  const result = analyzeWork({ DOI: "10.9999/example" });
  assert.equal(result.verdict, "clean");
  assert.equal(result.title, null);
});
