// Build the Python Lambda asset without Docker.
//
// The service is pure Python except for a few compiled dependencies that
// anthropic and fastapi pull in (pydantic-core, jiter). Those are fetched as
// manylinux x86_64 wheels for CPython 3.12, which is what the Lambda runtime
// runs, so the asset built on Windows or macOS is the one that runs there.
// boto3 is provided by the runtime and is left out to keep the asset small.
//
// spaCy is deliberately absent. Extraction runs where the transcript is.

import { execSync } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const out = path.join(root, "build", "lambda");
const venvPython =
  process.platform === "win32"
    ? path.join(root, ".venv", "Scripts", "python.exe")
    : path.join(root, ".venv", "bin", "python");
const python = fs.existsSync(venvPython) ? venvPython : "python";

function run(cmd) {
  console.log(`> ${cmd}`);
  execSync(cmd, { stdio: "inherit", cwd: root });
}

fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });

// Third-party dependencies, resolved for the Lambda platform.
run(
  `"${python}" -m pip install --quiet --target "${out}" ` +
    `--only-binary=:all: --platform manylinux2014_x86_64 --python-version 3.12 --implementation cp ` +
    `"fastapi>=0.115" "mangum>=0.17" "anthropic>=0.40"`,
);

// Our own packages, pure Python, without re-resolving their dependencies.
run(
  `"${python}" -m pip install --quiet --target "${out}" --no-deps ` +
    `"${path.join(root, "packages", "speech-vitals")}" ` +
    `"${path.join(root, "apps", "engine")}" ` +
    `"${path.join(root, "apps", "server")}"`,
);

// The simulated persona, so the demo profile seeds itself on first request.
const persona = path.join(root, "fixtures", "personas", "alex-drift");
const dest = path.join(out, "fixtures", "personas", "alex-drift");
fs.mkdirSync(dest, { recursive: true });
for (const f of ["days.json", "meta.json", "summary.json"]) {
  fs.copyFileSync(path.join(persona, f), path.join(dest, f));
}

// Trim what Lambda never needs.
for (const d of fs.readdirSync(out)) {
  if (d.endsWith(".dist-info") || d === "__pycache__") continue;
  const p = path.join(out, d);
  if (fs.statSync(p).isDirectory()) {
    for (const sub of ["tests", "test", "__pycache__"]) {
      fs.rmSync(path.join(p, sub), { recursive: true, force: true });
    }
  }
}

let bytes = 0;
const walk = (p) => {
  for (const e of fs.readdirSync(p, { withFileTypes: true })) {
    const q = path.join(p, e.name);
    if (e.isDirectory()) walk(q);
    else bytes += fs.statSync(q).size;
  }
};
walk(out);
console.log(`Lambda asset ready at ${out} (${(bytes / 1e6).toFixed(1)} MB)`);
