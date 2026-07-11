import { compileFromFile } from "json-schema-to-typescript";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const workbenchRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(workbenchRoot, "../..");
const exporter = path.join(repoRoot, "scripts/export_workbench_contracts.py");
const generatedDir = path.join(workbenchRoot, "src/generated");
const checkedSchema = path.join(generatedDir, "workbench-contracts.schema.json");
const checkedTypes = path.join(generatedDir, "workbench-contracts.ts");

async function generate(schemaPath, typesPath) {
  await mkdir(path.dirname(schemaPath), { recursive: true });
  const result = spawnSync("uv", ["run", "python", exporter, schemaPath], {
    cwd: repoRoot,
    encoding: "utf8",
    stdio: "inherit"
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`backend contract export failed with status ${result.status ?? "unknown"}`);
  }

  const source = await compileFromFile(schemaPath, {
    additionalProperties: false,
    unknownAny: true,
    bannerComment: "/* Generated from backend Pydantic contracts. Do not edit. */"
  });
  await writeFile(typesPath, source, "utf8");
}

async function check() {
  const temporaryDir = await mkdtemp(path.join(tmpdir(), "hardwise-contracts-"));
  try {
    const schemaPath = path.join(temporaryDir, "workbench-contracts.schema.json");
    const typesPath = path.join(temporaryDir, "workbench-contracts.ts");
    await generate(schemaPath, typesPath);
    const [expectedSchema, actualSchema, expectedTypes, actualTypes] = await Promise.all([
      readFile(checkedSchema),
      readFile(schemaPath),
      readFile(checkedTypes),
      readFile(typesPath)
    ]);
    if (!expectedSchema.equals(actualSchema) || !expectedTypes.equals(actualTypes)) {
      console.error("Generated Workbench contracts are stale. Run npm run generate:contracts.");
      process.exitCode = 1;
    }
  } finally {
    await rm(temporaryDir, { recursive: true, force: true });
  }
}

const mode = process.argv[2] ?? "generate";
if (mode === "generate") {
  await generate(checkedSchema, checkedTypes);
} else if (mode === "check") {
  await check();
} else {
  throw new Error(`unknown contract command: ${mode}`);
}
