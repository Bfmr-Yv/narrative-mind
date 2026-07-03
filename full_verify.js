const {execSync} = require('child_process');
const dir = 'C:\\Users\\userf\\Desktop\\narrative-mind\\src-tauri';
const pydir = 'C:\\Users\\userf\\Desktop\\narrative-mind\\src-python';
const crates = ['xmgl-core','xmgl-agent','xmgl-memory','xmgl-orchestrator','xmgl-python-bridge','xmgl-project','xmgl-tauri'];
const results = [];

for (const c of crates) {
  try {
    execSync('cargo test -p ' + c, {cwd: dir, timeout: 120000, stdio: 'pipe'});
    results.push(c + ': PASS');
  } catch(e) {
    results.push(c + ': FAIL exit=' + (e.status||'?'));
  }
}

try {
  execSync('cargo clippy --workspace --all-targets -- -D warnings', {cwd: dir, timeout: 60000, stdio: 'pipe'});
  results.push('clippy: PASS');
} catch(e) {
  results.push('clippy: FAIL exit=' + (e.status||'?'));
}

try {
  execSync('.\\.venv\\Scripts\\python.exe -c "from llm.client import get_client; print(get_client().is_available)"', {cwd: pydir, timeout: 10000, stdio: 'pipe'});
  results.push('python: PASS');
} catch(e) {
  results.push('python: FAIL');
}

try {
  execSync('npx tsc --noEmit', {cwd: 'C:\\Users\\userf\\Desktop\\narrative-mind', timeout: 30000, stdio: 'pipe'});
  results.push('tsc: PASS');
} catch(e) {
  results.push('tsc: FAIL exit=' + (e.status||'?'));
}

console.log(results.join('\n'));
require('fs').writeFileSync('C:\\Users\\userf\\Desktop\\narrative-mind\\full_verify.txt', results.join('\n'), 'utf8');
