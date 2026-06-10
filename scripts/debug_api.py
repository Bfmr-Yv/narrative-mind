"""调试 API 流程 — 模拟前端请求"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 完全复制 api_server.py 的初始化流程
from src.llm import get_config, LLMClient, CostTracker
from src.corpus_anchor.slice_manager import SliceManager
from src.corpus_anchor.embedder import Embedder
from src.corpus_anchor.retriever import Retriever
from src.corpus_anchor.enricher import Enricher
from src.engines.character import CharacterEngine, CharacterQuery
from src.engines.world import WorldEngine, WorldQuery
from src.consistency_guardian.guardian import ConsistencyGuardian, GuardianInput
from src.orchestrator.router import Orchestrator, UserAction
from src.project_manager import ProjectManager

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("=== Step 1: 初始化 LLM ===")
llm_config = get_config()
cost_tracker = CostTracker()
llm_client = LLMClient(config=llm_config, cost_tracker=cost_tracker)
print(f"  LLM available: {llm_client.is_available}")
print(f"  Model: {llm_config.model}")

print("\n=== Step 2: 初始化语料 ===")
_enricher = Enricher(project_id="default")
slice_manager = SliceManager()
embedder = Embedder()
retriever = Retriever(
    embedder=embedder, slice_manager=slice_manager,
    similarity_threshold=0.1, llm_client=llm_client, enricher=_enricher,
)
corpus_dir = os.path.join(_PROJECT_ROOT, "corpus")
slice_manager.load_slices(os.path.join(corpus_dir, "public-domain", "hong-lou-meng"))
slice_manager.load_slices(os.path.join(corpus_dir, "user"))
retriever.build_index()
print(f"  Slices: {retriever.slice_count}, Vocab: {embedder.vocabulary_size}")

print("\n=== Step 3: 初始化引擎 ===")
character_engine = CharacterEngine(retriever=retriever, llm_client=llm_client)
world_engine = WorldEngine(llm_client=llm_client)
settings_path = os.path.join(_PROJECT_ROOT, "config", "world-settings.json")
world_engine.load_settings(settings_path)
world_engine.load_character_power_levels({
    "贾宝玉": "普通人", "林黛玉": "普通人", "王熙凤": "普通人",
    "陈平安": "修行者", "路明非": "修行者",
})
guardian = ConsistencyGuardian()
orchestrator = Orchestrator(
    character_engine=character_engine, world_engine=world_engine,
    guardian=guardian, enricher=_enricher, retriever=retriever,
)
print(f"  All engines ready")

print("\n=== Step 4: 模拟前端 analyze 请求 ===")
action = UserAction(
    type="analyze",
    payload={
        "character_id": "贾宝玉",
        "scene_text": "贾宝玉在大观园中散步，见花开花落，心生感慨。",
        "event_description": "贾宝玉在大观园中散步",
        "location": "大观园",
        "involved_characters": ["贾宝玉"],
    },
)

result = orchestrator.execute(action)
print(f"  success: {result.success}")
print(f"  message: {result.message}")

# 检查角色引擎结果
char_result = result.engine_results.get("character_engine")
if char_result:
    print(f"\n  --- Character Engine ---")
    print(f"  PAD: P={char_result.pad_state.pleasure:.2f}, A={char_result.pad_state.arousal:.2f}, D={char_result.pad_state.dominance:.2f}")
    print(f"  行为: {char_result.behavior_prediction.predicted_action}")
    print(f"  备选: {char_result.behavior_prediction.alternative_actions}")
    print(f"  置信度: {char_result.confidence:.2f}")
    print(f"  需审核: {char_result.needs_human_review}")
else:
    print(f"  ❌ character_engine 结果为空!")

# 检查世界引擎结果
world_result = result.engine_results.get("world_engine")
if world_result:
    print(f"\n  --- World Engine ---")
    print(f"  空间一致: {world_result.spatial_consistency}")
    print(f"  力量等级: {world_result.power_level_validation.value}")
    print(f"  规则检查: {len(world_result.rule_checks)} 条")
else:
    print(f"  ❌ world_engine 结果为空!")

# 检查守卫结果
if result.guardian_output:
    g = result.guardian_output
    print(f"\n  --- Guardian ---")
    print(f"  警报级别: {g.alarm_level.value}")
    print(f"  需要动作: {g.action_required.value}")
    print(f"  冲突数: {len(g.conflicts)}")
    for c in g.conflicts:
        print(f"    [{c.level.value}] {c.dimension}: {c.detail}")

print(f"\n=== Cost: ${cost_tracker.current_month_total():.4f} ===")

# Step 5: 测试 to_json 序列化（这是 API 返回给前端的关键步骤）
print("\n=== Step 5: 模拟 JSON 序列化（api_server._to_json）===")
from src.api_server import _to_json
serialized = _to_json(result)
print(f"  success: {serialized.get('success')}")
print(f"  engine_results keys: {list(serialized.get('engine_results', {}).keys())}")
cr_json = serialized.get('engine_results', {}).get('character_engine', {})
if cr_json:
    print(f"  character_engine.pad_state: {cr_json.get('pad_state')}")
    print(f"  character_engine.behavior_prediction: {cr_json.get('behavior_prediction')}")
    print(f"  character_engine.confidence: {cr_json.get('confidence')}")
else:
    print(f"  ❌ 序列化后 character_engine 为空!")
    print(f"  原始数据: {serialized.get('engine_results', {})}")

print("\n=== DONE ===")
