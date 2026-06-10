import sys
import os

print("World Engine Test")
print("=" * 60)

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.engines.world import WorldEngine, WorldQuery, PowerLevel
    
    print("[1/2] Initializing World Engine...")
    engine = WorldEngine()
    
    # 加载设定
    print("[2/2] Loading settings...")
    settings_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "world-settings.json"
    )
    engine.load_settings(settings_path)
    print(f"  Settings loaded from: {settings_path}")
    
    # 加载角色力量等级
    engine.load_character_power_levels({
        "贾宝玉": "普通人",
        "林黛玉": "普通人",
        "王熙凤": "普通人",
        "陈平安": "修行者",
        "路明非": "修行者",
    })
    
    # 测试场景
    print("\n" + "=" * 60)
    print("Test Scenarios")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "贾宝玉在大观园",
            "query": WorldQuery(
                event_description="贾宝玉在大观园中散步",
                location="大观园",
                involved_characters=["贾宝玉"],
            ),
        },
        {
            "name": "陈平安在泥瓶巷",
            "query": WorldQuery(
                event_description="陈平安在泥瓶巷中行走",
                location="泥瓶巷",
                involved_characters=["陈平安"],
            ),
        },
        {
            "name": "路明非在卡塞尔学院",
            "query": WorldQuery(
                event_description="路明非在卡塞尔学院学习",
                location="卡塞尔学院",
                involved_characters=["路明非"],
            ),
        },
        {
            "name": "未知地点测试",
            "query": WorldQuery(
                event_description="某人在未知地点活动",
                location="未知地点",
                involved_characters=["贾宝玉"],
            ),
        },
        {
            "name": "多角色场景",
            "query": WorldQuery(
                event_description="贾宝玉和林黛玉在大观园中相见",
                location="大观园",
                involved_characters=["贾宝玉", "林黛玉"],
            ),
        },
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n[Test {i+1}] {test_case['name']}")
        print("-" * 40)
        
        try:
            response = engine.validate(test_case["query"])
            
            print(f"  Spatial Consistency: {response.spatial_consistency}")
            print(f"  Power Level: {response.power_level_validation.value}")
            
            if response.rule_checks:
                print(f"  Rule Checks:")
                for check in response.rule_checks:
                    status = "PASS" if check.passed else "FAIL"
                    print(f"    [{status}] {check.rule_name}: {check.detail}")
                    if check.conflict_description:
                        print(f"      Conflict: {check.conflict_description}")
            else:
                print(f"  Rule Checks: None")
            
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
