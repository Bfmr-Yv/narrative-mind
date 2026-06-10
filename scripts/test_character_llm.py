"""角色引擎 LLM 模式测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.corpus_anchor.slice_manager import SliceManager
from src.corpus_anchor.embedder import Embedder
from src.corpus_anchor.retriever import Retriever
from src.engines.character import CharacterEngine, CharacterQuery, EmotionContext, PADState
from src.llm import get_config, LLMClient, CostTracker

print("角色引擎 LLM 模式测试")
print("=" * 60)

# 初始化 LLM
config = get_config()
cost_tracker = CostTracker()
llm_client = LLMClient(config=config, cost_tracker=cost_tracker)
print(f"LLM: {config.model} (available={llm_client.is_available})")

# 初始化语料
slice_manager = SliceManager()
embedder = Embedder()
retriever = Retriever(embedder=embedder, slice_manager=slice_manager, llm_client=llm_client)

corpus_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpus")
slice_manager.load_slices(os.path.join(corpus_dir, "public-domain", "hong-lou-meng"))
slice_manager.load_slices(os.path.join(corpus_dir, "user"))
retriever.build_index()
print(f"Corpus: {retriever.slice_count} slices, vocab={embedder.vocabulary_size}")

# 初始化角色引擎
engine = CharacterEngine(retriever=retriever, llm_client=llm_client)

# 测试
test_cases = [
    CharacterQuery(
        character_id="贾宝玉",
        scene_text="宝玉早已看见多了一个姊妹，便料定是林姑妈之女，忙来作揖。厮见毕归坐，细看形容，与众各别。",
    ),
    CharacterQuery(
        character_id="林黛玉",
        scene_text="林黛玉正自悲泣，忽听院门响处，只见宝钗出来了，宝玉袭人一群人送了出来。待要上去问着宝玉，又恐当着众人问羞了宝玉不便，因而闪过一旁。",
    ),
    CharacterQuery(
        character_id="路明非",
        scene_text="路明非把信放下，摸了摸额头，有点发懵。本来看开头很对的一封信，一封标准的拒信，怎么过了那句之后忽然变了呢？",
    ),
]

for i, query in enumerate(test_cases):
    print(f"\n[Test {i+1}] {query.character_id}")
    print("-" * 40)
    response = engine.analyze(query)

    print(f"  PAD: (P={response.pad_state.pleasure:.2f}, A={response.pad_state.arousal:.2f}, D={response.pad_state.dominance:.2f})")
    print(f"  行为: {response.behavior_prediction.predicted_action}")
    print(f"  备选: {response.behavior_prediction.alternative_actions}")
    print(f"  置信度: {response.confidence:.2f}")
    print(f"  需人工审核: {response.needs_human_review}")
    if response.implicit_triggers:
        print(f"  触发: {response.implicit_triggers[:5]}")

print(f"\n成本追踪: spent=${cost_tracker.current_month_total():.4f}, remaining=${cost_tracker.remaining_budget():.2f}")
print("=" * 60)
print("测试完成!")
