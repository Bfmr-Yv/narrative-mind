const {execSync}=require('child_process');
const fs=require('fs');
const dir='C:\\Users\\userf\\Desktop\\narrative-mind\\src-tauri';
const pydir='C:\\Users\\userf\\Desktop\\narrative-mind\\src-python';
const r=[];
const crates=['xmgl-core','xmgl-agent','xmgl-memory','xmgl-orchestrator','xmgl-python-bridge','xmgl-project','xmgl-tauri'];
for(const c of crates){try{execSync('cargo test -p '+c,{cwd:dir,timeout:120000,stdio:'pipe'});r.push(c+':PASS');}catch(e){r.push(c+':FAIL');}}
try{execSync('cargo clippy --workspace --all-targets -- -D warnings',{cwd:dir,timeout:60000,stdio:'pipe'});r.push('clippy:PASS');}catch(e){r.push('clippy:FAIL');}
try{execSync('.\\.venv\\Scripts\\python.exe -c "from llm.client import get_client;print(get_client().is_available)"',{cwd:pydir,timeout:10000,stdio:'pipe'});r.push('py:PASS');}catch(e){r.push('py:FAIL');}
try{execSync('npx tsc --noEmit',{cwd:'C:\\Users\\userf\\Desktop\\narrative-mind',timeout:30000,stdio:'pipe'});r.push('tsc:PASS');}catch(e){r.push('tsc:FAIL');}
const out=r.join('\n');
console.log(out);
fs.writeFileSync('C:\\Users\\userf\\Desktop\\narrative-mind\\fv_result.txt',out);
