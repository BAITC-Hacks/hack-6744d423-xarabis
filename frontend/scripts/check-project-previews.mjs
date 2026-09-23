import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";

const output = mkdtempSync(join(tmpdir(), "akim-preview-tests-"));
const require = createRequire(import.meta.url);
try {
  execFileSync(
    process.execPath,
    [
      resolve("node_modules/typescript/bin/tsc"),
      "--module",
      "commonjs",
      "--target",
      "es2022",
      "--skipLibCheck",
      "--outDir",
      output,
      "src/projectPreview.ts",
      "src/caseData.ts",
    ],
    { stdio: "inherit" },
  );
  const { buildProjectPreviews, projectGeoJSON } = require(
    join(output, "projectPreview.js"),
  );
  const { MEASURES, DISTRICTS, REFERENCE_DECISIONS } = require(
    join(output, "caseData.js"),
  );
  assert.deepEqual(buildProjectPreviews([], MEASURES), []);
  assert.deepEqual(
    buildProjectPreviews([{ measureId: "missing" }], MEASURES),
    [],
  );
  for (const measure of MEASURES) {
    const decision = {
      measureId: measure.id,
      ...(measure.scope === "district" ? { districtId: "nura" } : {}),
    };
    const projects = buildProjectPreviews([decision], MEASURES);
    assert.equal(
      projects.length,
      measure.scope === "district" ? 1 : DISTRICTS.length,
    );
    assert.equal(new Set(projects.map((p) => p.id)).size, projects.length);
    for (const project of projects) {
      assert.ok(project.coordinates.every(Number.isFinite));
      assert.equal(project.label, measure.name);
      assert.ok(projectGeoJSON([project]).features.length > 0);
    }
  }
  const snapshot = JSON.stringify(REFERENCE_DECISIONS);
  const projects = buildProjectPreviews(REFERENCE_DECISIONS, MEASURES);
  const reordered = buildProjectPreviews(
    [...REFERENCE_DECISIONS].reverse(),
    MEASURES,
  );
  for (const project of projects)
    assert.deepEqual(
      project,
      reordered.find((p) => p.id === project.id),
    );
  assert.equal(
    JSON.stringify(REFERENCE_DECISIONS),
    snapshot,
    "Presentation must not mutate decisions",
  );
  const removed = buildProjectPreviews(
    REFERENCE_DECISIONS.filter((d) => d.measureId !== "M7"),
    MEASURES,
  );
  assert.ok(removed.every((p) => p.measureId !== "M7"));
  const moved = buildProjectPreviews(
    [{ measureId: "M7", districtId: "esil" }],
    MEASURES,
  );
  assert.equal(moved[0].districtId, "esil");
  assert.notDeepEqual(
    moved[0].coordinates,
    projects.find((p) => p.measureId === "M7").coordinates,
  );
  assert.deepEqual(projectGeoJSON([]), {
    type: "FeatureCollection",
    features: [],
  });
  console.log(
    "PASS: all 14 measure previews, city expansion, stable positions, removal, reassignment and input immutability",
  );
} finally {
  rmSync(output, { recursive: true, force: true });
}
