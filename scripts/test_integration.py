import sys
import os

print("End-to-End Integration Test")
print("=" * 60)

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.corpus_anchor.slice_manager import SliceManager
    from src.corpus_anchor.embedder import Embedder
    from src.corpus_anchor.retriever import Retriever
    from src.engines.character import CharacterEngine
    from src.engines.world import WorldEngine
    from src.consistency_guardian.guardian import ConsistencyGuardian
    from src.orchestrator.router import Orchestrator, UserAction
    from src.memory.working_memory import WorkingMemory, MemoryWrite, MemoryQuery
    
    print("[1/6] Initializing components...")
    
    # 初始化语料锚定层
    slice_manager = SliceManager()
    embedder = Embedder()
    retriever = Retriever(embedder=embedder, slice_manager=slice_manager, similarity_threshold=0.1)
    
    # 加载语料
    print("[2/6] Loading corpus...")
    corpus_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpus")
    slice_manager.load_slices(os.path.join(corpus_dir, "public-domain", "hong-lou-meng"))
    slice_manager.load_slices(os.path.join(corpus_dir, "user"))
    print(f"  Loaded {len(slice_manager.get_all_slices())} slices")
    
    # 构建索引
    print("[3/6] Building index...")
    retriever.build_index()
    print(f"  Vocabulary size: {embedder.vocabulary_size}")
    
    # 初始化引擎
    print("[4/6] Initializing engines...")
    character_engine = CharacterEngine(retriever=retriever)
    
    world_engine = WorldEngine()
    settings_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "world-settings.json"
    )
    world_engine.load_settings(settings_path)
    world_engine.load_character_power_levels({
        "贾宝玉": "普通人",
        "林黛玉": "普通人",
        "王熙凤": "普通人",
        "陈平安": "修行者",
        "路明非": "修行者",
    })
    
    guardian = ConsistencyGuardian()
    orchestrator = Orchestrator(
        character_engine=character_engine,
        world_engine=world_engine,
        guardian=guardian,
    )
    
    memory = WorkingMemory()
    print("  All engines initialized!")
    
    # 测试场景
    print("\n[5/6] Testing scenarios...")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "贾宝玉在大观园",
            "action": UserAction(
                type="analyze",
                payload={
                    "character_id": "贾宝玉",
                    "scene_text": "贾宝玉在大观园中散步，心情愉悦",
                    "event_description": "贾宝玉在大观园中散步",
                    "location": "大观园",
                    "involved_characters": ["贾宝玉"],
                },
            ),
        },
        {
            "name": "林黛玉葬花",
            "action": UserAction(
                type="predict",
                payload={
                    "character_id": "林黛玉",
                    "scene_text": "林黛玉正自悲泣，忽听院门响处，只见宝钗出来了",
                },
            ),
        },
        {
            "name": "未知地点测试",
            "action": UserAction(
                type="check",
                payload={
                    "event_description": "某人在未知地点活动",
                    "location": "未知地点",
                    "involved_characters": ["贾宝玉"],
                },
            ),
        },
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n[Test {i+1}] {test_case['name']}")
        print("-" * 40)
        
        try:
            result = orchestrator.execute(test_case["action"])
            
            print(f"  Success: {result.success}")
            print(f"  Message: {result.message}")
            
            if result.guardian_output:
                print(f"  Guardian Alarm Level: {result.guardian_output.alarm_level.value}")
                print(f"  Action Required: {result.guardian_output.action_required.value}")
                
                if result.guardian_output.conflicts:
                    print(f"  Conflicts:")
                    for conflict in result.guardian_output.conflicts:
                        print(f"    [{conflict.level.value}] {conflict.dimension}: {conflict.detail}")
            
            # 写入记忆
            if result.success:
                memory.write(MemoryWrite(
                    source_engine="orchestrator",
                    target_tier="working",
                    memory_type="analysis_result",
                    data={
                        "action_type": test_case["action"].type,
                        "success": result.success,
                    },
                ))
            
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
    
    # 测试记忆系统
    print("\n" + "=" * 60)
    print("[6/6] Testing memory system...")
    print("-" * 40)
    
    print(f"  Memory size: {memory.size()}")
    
    # 读取记忆
    query = MemoryQuery(tier="working", top_k=5)
    entries = memory.read(query)
    print(f"  Retrieved {len(entries)} entries")
    
    for entry in entries:
        print(f"    - {entry.key}: {entry.data}")
    
    print("\n" + "=" * 60)
    print("Integration Test completed!")
    print("=" * 60)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
