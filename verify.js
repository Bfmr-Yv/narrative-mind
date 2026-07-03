#!/usr/bin/env node
/**
 * Narrative Mind v4.0 — 全面代码审查 + 验证脚本
 * 运行: node verify.js
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT = __dirname;
const results = [];
let passCount = 0;
let failCount = 0;

function check(name, fn) {
  try {
    const result = fn();
    if (result === true || result === undefined) {
      results.push(`✅ ${name}`);
      passCount++;
    } else {
      results.push(`❌ ${name}: ${result}`);
      failCount++;
    }
  } catch (e) {
    results.push(`❌ ${name}: ${e.message}`);
    failCount++;
  }
}

function readFile(rel) {
  return fs.readFileSync(path.join(ROOT, rel), 'utf8');
}

function fileExists(rel) {
  return fs.existsSync(path.join(ROOT, rel));
}

// ============================================================
// 1. 文件存在性检查
// ============================================================
results.push('\n=== 1. 文件存在性 ===');

check('config/llm.json 存在', () => fileExists('config/llm.json') || '文件不存在');
check('src-python/main.py 存在', () => fileExists('src-python/main.py') || '文件不存在');
check('src-python/llm/client.py 存在', () => fileExists('src-python/llm/client.py') || '文件不存在');
check('src-python/llm/config.py 存在', () => fileExists('src-python/llm/config.py') || '文件不存在');
check('src-frontend/src/api/analysis.ts 存在', () => fileExists('src-frontend/src/api/analysis.ts') || '文件不存在');
check('src-frontend/src/api/events.ts 存在', () => fileExists('src-frontend/src/api/events.ts') || '文件不存在');

// ============================================================
// 2. Rust LLMCallRequest 结构检查
// ============================================================
results.push('\n=== 2. Rust LLMCallRequest 结构 ===');

const bridgeSrc = readFile('src-tauri/crates/xmgl-python-bridge/src/lib.rs');

check('LLMCallRequest 有 system_prompt_key 字段', () => 
  bridgeSrc.includes('pub system_prompt_key: String') || '缺少 system_prompt_key');

check('LLMCallRequest 有 system_prompt 字段', () => 
  bridgeSrc.includes('pub system_prompt: String') || '缺少 system_prompt');

check('call_agent 填充 system_prompt', () => 
  bridgeSrc.includes('system_prompt: rendered.system_prompt') || 'call_agent 未填充 system_prompt');

check('call_agent 填充 user_message', () => 
  bridgeSrc.includes('user_message: rendered.user_message') || 'call_agent 未填充 user_message');

// ============================================================
// 3. Python main.py 检查
// ============================================================
results.push('\n=== 3. Python main.py ===');

const mainPy = readFile('src-python/main.py');

check('LLMCallRequest 有 system_prompt 字段', () => 
  mainPy.includes('system_prompt: str') || '缺少 system_prompt 字段');

check('llm_call 使用 system_prompt', () => 
  mainPy.includes('req.system_prompt if req.system_prompt else req.system_prompt_key') || 
  '未正确使用 system_prompt fallback');

check('llm_call 不直接用 system_prompt_key 作为 prompt', () => {
  // 检查是否还存在旧的错误用法
  const match = mainPy.match(/system_prompt=req\.system_prompt_key/);
  return match ? '仍然直接使用 system_prompt_key 作为 prompt' : true;
});

check('health 端点返回 llm_available', () => 
  mainPy.includes('"llm_available"') || 'health 端点缺少 llm_available');

check('health 端点返回 model', () => 
  mainPy.includes('"model": cfg.model') || 'health 端点缺少 model');

// ============================================================
// 4. Python config.py 检查
// ============================================================
results.push('\n=== 4. Python config.py ===');

const configPy = readFile('src-python/llm/config.py');

check('config.py 有 MiMo provider', () => 
  configPy.includes('MIMO_BASE_URL') || '缺少 MiMo provider');

check('config.py 有 MiMo Pro 模型', () => 
  configPy.includes('mimo-v2.5-pro') || '缺少 mimo-v2.5-pro');

check('config.py 有 MiMo Flash 模型', () => 
  configPy.includes('mimo-v2.5') || '缺少 mimo-v2.5');

check('config.py 支持 MIMO_API_KEY 环境变量', () => 
  configPy.includes('MIMO_API_KEY') || '缺少 MIMO_API_KEY 支持');

check('get_config 从文件检测 provider', () => 
  configPy.includes('file_config.get("provider"') || '未从配置文件检测 provider');

// ============================================================
// 5. config/llm.json 检查
// ============================================================
results.push('\n=== 5. config/llm.json ===');

const llmJson = JSON.parse(readFile('config/llm.json'));

check('llm.json provider 是 mimo', () => 
  llmJson.provider === 'mimo' || `provider 是 ${llmJson.provider}`);

check('llm.json base_url 是 MiMo Token Plan', () => 
  llmJson.base_url.includes('token-plan-cn.xiaomimimo.com') || `base_url 是 ${llmJson.base_url}`);

check('llm.json api_key 不为空', () => 
  (llmJson.api_key && llmJson.api_key.length > 5) || 'api_key 为空或过短');

check('llm.json model 是 mimo-v2.5-pro', () => 
  llmJson.model === 'mimo-v2.5-pro' || `model 是 ${llmJson.model}`);

// ============================================================
// 6. Orchestrator 检查
// ============================================================
results.push('\n=== 6. Orchestrator ===');

const orchSrc = readFile('src-tauri/crates/xmgl-orchestrator/src/lib.rs');

check('predict_complexity 有文本长度判断', () => 
  orchSrc.includes('text_length < 200') || '缺少文本长度判断');

check('predict_complexity 有任务类型约束', () => 
  orchSrc.includes('min_for_task') || '缺少任务类型约束');

check('upgrade_topology 存在', () => 
  orchSrc.includes('fn upgrade_topology') || '缺少 upgrade_topology');

check('run_analysis 有 HCP-MAD 升级逻辑', () => 
  orchSrc.includes('upgrade_round') || '缺少升级逻辑');

check('default_agent_for 覆盖 Rerank', () => 
  orchSrc.includes('TaskType::Rerank') || '缺少 Rerank 映射');

check('default_agent_for 覆盖 EntityExtract', () => 
  orchSrc.includes('TaskType::EntityExtract') || '缺少 EntityExtract 映射');

check('default_agent_for 覆盖 SpatialCheck', () => 
  orchSrc.includes('TaskType::SpatialCheck') || '缺少 SpatialCheck 映射');

// ============================================================
// 7. Agent 检查
// ============================================================
results.push('\n=== 7. Agent ===');

const agentSrc = readFile('src-tauri/crates/xmgl-agent/src/lib.rs');

check('SharedContext 有 metadata 字段', () => 
  agentSrc.includes('pub metadata: HashMap') || '缺少 metadata');

check('SharedContext 有 chapter_title 字段', () => 
  agentSrc.includes('pub chapter_title: Option<String>') || '缺少 chapter_title');

check('collect_prior_outputs 存在', () => 
  agentSrc.includes('fn collect_prior_outputs') || '缺少 collect_prior_outputs');

check('EditorInChiefAgent 汇总前序输出', () => 
  agentSrc.includes('agent_outputs') && agentSrc.includes('collect_prior_outputs') || 
  'EditorInChiefAgent 未汇总输出');

check('NarrativeAgent 读取 CharacterAgent 输出', () => 
  agentSrc.includes('AgentId::Character') && agentSrc.includes('character_analysis') || 
  'NarrativeAgent 未读取 CharacterAgent 输出');

check('EconomyAgent 传 word_count', () => 
  agentSrc.includes('"word_count"') || 'EconomyAgent 未传 word_count');

check('有 9 个 agent_impl 调用', () => {
  const count = (agentSrc.match(/agent_impl!\(/g) || []).length;
  return count === 9 || `只有 ${count} 个 agent_impl`;
});

// ============================================================
// 8. Tauri commands 检查
// ============================================================
results.push('\n=== 8. Tauri Commands ===');

const cmdSrc = readFile('src-tauri/crates/xmgl-tauri/src/commands.rs');

check('run_analysis 复用 request_id', () => 
  cmdSrc.includes('request_id = request.request_id.clone()') || '未复用 request_id');

check('run_analysis 构建 SharedContext', () => 
  cmdSrc.includes('SharedContext::new') || '未构建 SharedContext');

check('main.rs 注册 run_analysis', () => {
  const mainSrc = readFile('src-tauri/src/main.rs');
  return mainSrc.includes('commands::run_analysis') || '未注册 run_analysis';
});

// ============================================================
// 9. 前端检查
// ============================================================
results.push('\n=== 9. 前端 ===');

const analysisTs = readFile('src-frontend/src/api/analysis.ts');
const eventsTs = readFile('src-frontend/src/api/events.ts');
const indexTs = readFile('src-frontend/src/api/index.ts');

check('analysis.ts 导出 runAnalysis', () => 
  analysisTs.includes('export async function runAnalysis') || '缺少 runAnalysis');

check('analysis.ts 导出 AnalysisOutput 类型', () => 
  analysisTs.includes('export interface AnalysisOutput') || '缺少 AnalysisOutput');

check('events.ts 导出 onAgentProgress', () => 
  eventsTs.includes('export function onAgentProgress') || '缺少 onAgentProgress');

check('events.ts 导出 onProposalReady', () => 
  eventsTs.includes('export function onProposalReady') || '缺少 onProposalReady');

check('events.ts 导出 onAnalysisComplete', () => 
  eventsTs.includes('export function onAnalysisComplete') || '缺少 onAnalysisComplete');

check('index.ts 导出 analysis 模块', () => 
  indexTs.includes('from "./analysis"') || '未导出 analysis');

check('index.ts 导出 events 模块', () => 
  indexTs.includes('from "./events"') || '未导出 events');

// ============================================================
// 10. 逻辑一致性检查（跨文件）
// ============================================================
results.push('\n=== 10. 跨文件一致性 ===');

check('Python health 返回字段与 Rust HealthStatus 一致', () => {
  const healthStatus = bridgeSrc.match(/pub struct HealthStatus[\s\S]*?^}/m);
  if (!healthStatus) return '找不到 HealthStatus';
  const hasStatus = bridgeSrc.includes('pub status: String');
  const hasLlmAvail = bridgeSrc.includes('pub llm_available: bool');
  const hasModel = bridgeSrc.includes('pub model: String');
  const pyHasStatus = mainPy.includes('"status": "ok"');
  const pyHasLlmAvail = mainPy.includes('"llm_available"');
  const pyHasModel = mainPy.includes('"model": cfg.model');
  if (!hasStatus || !hasLlmAvail || !hasModel) return 'Rust HealthStatus 字段不完整';
  if (!pyHasStatus || !pyHasLlmAvail || !pyHasModel) return 'Python health 返回字段不完整';
  return true;
});

check('Python CorpusSearchRequest 字段名与 Rust 一致', () => {
  const rustQuery = bridgeSrc.includes('"query_text": query');
  const pyQuery = mainPy.includes('query_text: str');
  return (rustQuery && pyQuery) || 'query_text 字段不一致';
});

check('Python RenderedPrompt 字段与 Rust 一致', () => {
  const rustUserMsg = bridgeSrc.includes('pub user_message: String');
  const pyUserMsg = mainPy.includes('"user_message"');
  return (rustUserMsg && pyUserMsg) || 'user_message 字段不一致';
});

// ============================================================
// 输出结果
// ============================================================
results.push(`\n${'='.repeat(50)}`);
results.push(`总计: ${passCount} 通过, ${failCount} 失败`);
results.push(`${'='.repeat(50)}`);

const output = results.join('\n');
console.log(output);
fs.writeFileSync('verify_results.txt', output, 'utf8');
