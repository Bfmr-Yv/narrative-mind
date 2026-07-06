const { execSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const root = path.resolve(__dirname, "..");
const tauriDir = path.join(root, "src-tauri");
const crates = [
  "xmgl-core",
  "xmgl-agent",
  "xmgl-memory",
  "xmgl-orchestrator",
  "xmgl-python-bridge",
  "xmgl-project",
  "xmgl-tauri",
];

const results = [];
for (const c of crates) {
  try {
    execSync(`cargo test -p ${c}`, {
      cwd: tauriDir,
      timeout: 120000,
      stdio: "pipe",
    });
    results.push(`${c}: PASS`);
  } catch (e) {
    results.push(`${c}: FAIL`);
  }
}

try {
  execSync("cargo clippy --workspace --all-targets -- -D warnings", {
    cwd: tauriDir,
    timeout: 60000,
    stdio: "pipe",
  });
  results.push("clippy: PASS");
} catch (e) {
  results.push("clippy: FAIL");
}

try {
  execSync("npx tsc --noEmit", {
    cwd: path.join(root, "src-frontend"),
    timeout: 30000,
    stdio: "pipe",
  });
  results.push("tsc: PASS");
} catch (e) {
  results.push("tsc: FAIL");
}

fs.writeFileSync(path.join(root, "vt_result.txt"), results.join("\n"));
console.log(results.join("\n"));
