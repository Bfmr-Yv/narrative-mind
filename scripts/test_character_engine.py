import sys
import os

print("Character Engine Test")
print("=" * 60)

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.corpus_anchor.slice_manager import SliceManager
    from src.corpus_anchor.embedder import Embedder
    from src.corpus_anchor.retriever import Retriever
    from src.engines.character import CharacterEngine, CharacterQuery, EmotionContext, PADState
    
    print("[1/4] Initializing components...")
    
    # 初始化语料锚定层
    slice_manager = SliceManager()
    embedder = Embedder()
    retriever = Retriever(embedder=embedder, slice_manager=slice_manager, similarity_threshold=0.1)
    
    # 加载语料
    print("[2/4] Loading corpus...")
    corpus_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpus")
    slice_manager.load_slices(os.path.join(corpus_dir, "public-domain", "hong-lou-meng"))
    slice_manager.load_slices(os.path.join(corpus_dir, "user"))
    print(f"  Loaded {len(slice_manager.get_all_slices())} slices")
    
    # 构建索引
    print("[3/4] Building index...")
    retriever.build_index()
    print(f"  Vocabulary size: {embedder.vocabulary_size}")
    
    # 初始化角色引擎
    print("[4/4] Initializing Character Engine...")
    engine = CharacterEngine(retriever=retriever)
    print("  Ready!")
    
    # 测试场景
    print("\n" + "=" * 60)
    print("Test Scenarios")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "贾宝玉初见林黛玉",
            "query": CharacterQuery(
                character_id="贾宝玉",
                scene_text="宝玉早已看见多了一个姊妹，便料定是林姑妈之女，忙来作揖。厮见毕归坐，细看形容，与众各别。",
            ),
        },
        {
            "name": "林黛玉葬花",
            "query": CharacterQuery(
                character_id="林黛玉",
                scene_text="林黛玉正自悲泣，忽听院门响处，只见宝钗出来了，宝玉袭人一群人送了出来。",
                emotion_context=EmotionContext(
                    target_emotion="melancholic"
                ),
            ),
        },
        {
            "name": "王熙凤出场",
            "query": CharacterQuery(
                character_id="王熙凤",
                scene_text="一语未了，只听后院中有人笑声，说：我来迟了，不曾迎接远客！",
            ),
        },
        {
            "name": "陈平安在泥瓶巷",
            "query": CharacterQuery(
                character_id="陈平安",
                scene_text="二月二，龙抬头。暮色里，小镇名叫泥瓶巷的僻静地方，有位孤苦伶仃的清瘦少年。",
            ),
        },
        {
            "name": "路明非收到录取通知",
            "query": CharacterQuery(
                character_id="路明非",
                scene_text="路明非把信放下，摸了摸额头，有点发懵。本来看开头很对的一封信，一封标准的拒信。",
            ),
        },
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n[Test {i+1}] {test_case['name']}")
        print("-" * 40)
        
        try:
            response = engine.analyze(test_case["query"])
            
            print(f"  PAD State:")
            print(f"    Pleasure:  {response.pad_state.pleasure:.2f}")
            print(f"    Arousal:   {response.pad_state.arousal:.2f}")
            print(f"    Dominance: {response.pad_state.dominance:.2f}")
            
            print(f"  Behavior Prediction:")
            print(f"    Action:     {response.behavior_prediction.predicted_action}")
            print(f"    Confidence: {response.behavior_prediction.confidence:.2f}")
            
            if response.behavior_prediction.alternative_actions:
                print(f"    Alternatives: {response.behavior_prediction.alternative_actions}")
            
            print(f"  Overall Confidence: {response.confidence:.2f}")
            print(f"  Needs Human Review: {response.needs_human_review}")
            
            if response.implicit_triggers:
                print(f"  Implicit Triggers: {response.implicit_triggers[:5]}")
            
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
