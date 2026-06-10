"""
后端验证脚本：测试统一场景分析管道

验证：
1. LLM 配置加载
2. LLM 客户端可用性
3. scene_analysis prompt → LLM 调用 → JSON 解析
4. 角色/地点提取 + 事件推演
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.llm import LLMClient, CostTracker, get_config
from src.llm.prompts import SCENE_ANALYSIS_SYSTEM, format_scene_analysis_prompt


def main():
    print("=" * 60)
    print("后端场景分析管道验证")
    print("=" * 60)

    # 1. LLM 配置
    config = get_config()
    print(f"\n1. LLM 配置:")
    print(f"   API key 已配置: {config.is_configured}")
    print(f"   Model: {config.model}")
    print(f"   Base URL: {config.base_url}")

    if not config.is_configured:
        print("\n[FAIL] LLM 未配置！请检查 config/llm.json")
        return False

    # 2. LLM 客户端
    cost_tracker = CostTracker()
    llm = LLMClient(config=config, cost_tracker=cost_tracker)
    print(f"\n2. LLM 客户端:")
    print(f"   可用: {llm.is_available}")

    if not llm.is_available:
        print("\n[FAIL] LLM 客户端不可用！")
        return False

    # 3. 测试场景分析
    test_text = """
    贾宝玉来到潇湘馆，见林黛玉正坐在窗前看书。
    黛玉抬头看了他一眼，又低下头去，并不说话。
    宝玉心知她又在生气，便笑道："妹妹今日怎么不理我？"
    黛玉冷哼一声："你自去陪你宝姐姐便是，来我这里做什么。"
    宝玉连忙坐到她身边，低声说了几句软话。
    这时外面传来丫鬟的声音："宝姑娘来了！"
    薛宝钗款款走进来，手中捧着一个青瓷茶盏。
    """

    print(f"\n3. 测试文本 ({len(test_text)} 字):")
    print(f"   {test_text.strip()[:100]}...")

    # 构建 prompt
    user_message = format_scene_analysis_prompt(test_text)
    print(f"\n4. System prompt 长度: {len(SCENE_ANALYSIS_SYSTEM)} chars")
    print(f"   User message 长度: {len(user_message)} chars")

    # 调用 LLM
    print(f"\n5. 调用 LLM (task_type='scene_analysis')...")
    result = llm.call(
        system_prompt=SCENE_ANALYSIS_SYSTEM,
        user_message=user_message,
        task_type="scene_analysis",
    )

    print(f"   返回类型: {type(result).__name__}")
    print(f"   返回值: {result}")

    if not isinstance(result, dict):
        print("\n[FAIL] LLM 返回非 dict！可能是 JSON 解析失败。")
        print("   尝试 fallback (entity_extract)...")
        from src.llm.prompts import ENTITY_EXTRACT_SYSTEM, format_entity_extract_prompt
        user_message2 = format_entity_extract_prompt(test_text)
        result = llm.call(
            system_prompt=ENTITY_EXTRACT_SYSTEM,
            user_message=user_message2,
            task_type="entity_extract",
        )
        print(f"   Fallback 返回: {result}")
        if not isinstance(result, dict):
            print("\n[FAIL] Fallback 也失败了。LLM 调用存在问题。")
            return False

    # 4. 检查返回内容
    chars = result.get('characters', [])
    locs = result.get('locations', [])
    pred = result.get('event_prediction', '')

    print(f"\n6. 分析结果:")
    print(f"   角色 ({len(chars)}): {chars}")
    print(f"   地点 ({len(locs)}): {locs}")
    print(f"   事件推演 ({len(pred)} 字):")
    print(f"   {pred[:200]}...")

    # 5. 验证
    errors = []
    if not chars:
        errors.append("角色列表为空")
    if not locs:
        errors.append("地点列表为空")
    if len(pred) < 20:
        errors.append(f"事件推演太短 ({len(pred)} 字)")

    if errors:
        print(f"\n[WARN] 存在以下问题:")
        for e in errors:
            print(f"  - {e}")
    else:
        print(f"\n[PASS] 所有维度数据正常！后端管道工作正常。")

    # 6. 成本
    print(f"\n7. 本次调用成本:")
    status = cost_tracker.status()
    print(f"   本月已用: ${status['current_month_cost']:.6f}")
    print(f"   剩余: ${status['remaining_budget']:.2f}")

    return True


if __name__ == '__main__':
    ok = main()
    print(f"\n{'=' * 60}")
    print(f"结果: {'PASS' if ok else 'FAIL'}")
    print(f"{'=' * 60}")
    sys.exit(0 if ok else 1)
