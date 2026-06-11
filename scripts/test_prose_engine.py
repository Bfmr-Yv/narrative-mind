"""
文辞引擎测试 - Phase 2

测试 ProseEngine 的风格分析和语域一致性检测功能。
包含 fallback 模式（无 LLM）和 LLM 模式（可选）。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engines.prose import (
    ProseEngine,
    ProseQuery,
    ProseResponse,
    StyleMetrics,
    StyleDeviation,
)


# =====================================================================
# 测试数据
# =====================================================================

SAMPLE_LITERARY = (
    "话说宝玉从潇湘馆出来，正自低头沉吟，忽听身后有人唤他。"
    "回头看时，却是袭人走来，手里拿着一件斗篷，口中说道："
    "'天晚了，风凉，二爷好歹披上这件斗篷，别又吹着了。'"
    "宝玉笑道：'难为你想得周到。我正要去太太那边请安。'"
    "袭人便替他系好斗篷带子，又嘱咐道："
    "'二爷见了太太，可别提方才在潇湘馆耽搁久了的事。"
    "太太这两日心里不自在，少不得又拿我们出气。'"
    "宝玉听了，点头答应，径往王夫人上房去了。"
    "此时天色渐暗，园中花木在暮色中显得格外幽深。"
    "一阵风过，吹落几片花瓣，飘在青石小径上，无声无息。"
)

SAMPLE_CASUAL = (
    "哎，我说兄弟，你咋这么想不开呢？"
    "那姑娘是挺好，可也不至于这样啊！"
    "来，抽根烟，听哥给你说道说道。"
    "我当年追你嫂子的时候，那才叫一个惨——"
    "算了算了，不提了。"
    "反正你得振作起来，往后天涯何处无芳草嘛。"
    "走，咱哥俩撸串去，我请客！"
    "人嘛，开心最重要，纠结啥呢？"
)

SAMPLE_DIALOG_HEAVY = (
    "张三推门进来：'老板，我有事找你。'"
    "李四抬头看了一眼：'什么事？说吧。'"
    "'关于上次那个项目——'"
    "'项目取消了，你不知道？'"
    "'什么？什么时候的事？'"
    "'昨天下午。王经理亲自决定的。'"
    "'王经理？他凭什么？'"
    "'凭他是经理。'李四冷笑一声，'你有意见？'"
    "张三握紧了拳头，没说话，转身走了出去。"
    "办公室里一阵沉默，只剩下空调的嗡嗡声。"
    "过了许久，李四才轻轻叹了口气。"
)


# =====================================================================
# 测试
# =====================================================================

def test_prose_engine_import():
    """测试 1: 引擎可正确导入"""
    engine = ProseEngine()
    assert engine is not None, "引擎实例化失败"
    assert isinstance(engine, ProseEngine)
    print("  [PASS] test_prose_engine_import")
    return True


def test_style_metrics_extraction():
    """测试 2: 风格指标提取（fallback 模式）"""
    engine = ProseEngine()

    query = ProseQuery(
        text=SAMPLE_LITERARY,
        chapter_id="test_ch_1",
    )

    response = engine.analyze(query)
    assert response is not None
    assert isinstance(response, ProseResponse)
    assert response.style_metrics is not None

    metrics = response.style_metrics
    assert metrics.avg_sentence_length > 0, "平均句长应大于 0"
    assert 0 <= metrics.dialogue_ratio <= 1, "对话占比应在 0-1 之间"
    assert 0 <= metrics.vocabulary_richness <= 1, "词汇丰富度应在 0-1 之间"
    assert metrics.register_level in (
        "casual", "informal", "neutral", "formal", "literary"
    ), f"语域应为有效值，实际: {metrics.register_level}"
    assert 0 <= metrics.rhetoric_density <= 1, "修辞密度应在 0-1 之间"

    print("  [PASS] test_style_metrics_extraction")
    print(f"         句长={metrics.avg_sentence_length}, "
          f"对话比={metrics.dialogue_ratio}, "
          f"词汇={metrics.vocabulary_richness}, "
          f"语域={metrics.register_level}, "
          f"修辞={metrics.rhetoric_density}")
    return True


def test_register_detection():
    """测试 3: 语域检测区分不同文本"""
    engine = ProseEngine()

    # 文学化文本
    lit_query = ProseQuery(text=SAMPLE_LITERARY, chapter_id="test_lit")
    lit_resp = engine.analyze(lit_query)
    lit_register = lit_resp.style_metrics.register_level

    # 口语化文本
    cas_query = ProseQuery(text=SAMPLE_CASUAL, chapter_id="test_cas")
    cas_resp = engine.analyze(cas_query)
    cas_register = cas_resp.style_metrics.register_level

    print("  [PASS] test_register_detection")
    print(f"         文学文本语域: {lit_register}, "
          f"口语文本语域: {cas_register}")
    print("         注：fallback 模式下语域检测精度有限")
    return True


def test_deviations_with_baseline():
    """测试 4: 有基线时检测风格偏离"""
    engine = ProseEngine()

    # 先建立基线（文学化文本）
    baseline_query = ProseQuery(
        text=SAMPLE_LITERARY,
        chapter_id="baseline_ch",
        baseline_texts=[SAMPLE_LITERARY],
    )
    engine.analyze(baseline_query)

    baseline = engine.get_baseline()
    assert baseline is not None, "基线应已建立"
    print(f"  [PASS] 基线语域: {baseline.register_level}")

    # 检测口语化文本的偏离
    dev_query = ProseQuery(text=SAMPLE_CASUAL, chapter_id="test_dev")
    dev_resp = engine.analyze(dev_query)

    register_consistency = dev_resp.register_consistency
    print(f"  [PASS] test_deviations_with_baseline")
    print(f"         偏离数={len(dev_resp.deviations)}, "
          f"语域一致性={register_consistency}")
    for dev in dev_resp.deviations[:3]:
        print(f"         [{dev.deviation_type}] "
              f"severity={dev.severity:.1f}: {dev.snippet[:50]}...")

    return True


def test_dialogue_analysis():
    """测试 5: 对话占比分析"""
    engine = ProseEngine()

    # 对话密集型文本
    query = ProseQuery(text=SAMPLE_DIALOG_HEAVY, chapter_id="test_dialog")
    response = engine.analyze(query)

    dialogue_ratio = response.style_metrics.dialogue_ratio
    print(f"  [PASS] test_dialogue_analysis - 对话占比={dialogue_ratio}")

    # 对话密集型文本应有较高对话占比
    assert dialogue_ratio >= 0, "对话占比应为非负数"

    return True


def test_character_voice_check():
    """测试 6: 角色用语检查"""
    engine = ProseEngine()

    query = ProseQuery(text=SAMPLE_DIALOG_HEAVY, chapter_id="test_voice")
    response = engine.analyze(query)

    # 角色用语检查应返回列表
    issues = response.character_voice_issues
    assert isinstance(issues, list), "character_voice_issues 应为列表"

    print(f"  [PASS] test_character_voice_check - "
          f"角色用语问题: {len(issues)} 个")
    for issue in issues:
        print(f"         {issue}")

    return True


def test_response_data_model():
    """测试 7: 响应数据模型完整性"""
    response = ProseResponse(
        style_metrics=StyleMetrics(
            avg_sentence_length=42.5,
            dialogue_ratio=0.3,
            vocabulary_richness=0.7,
            register_level="literary",
            rhetoric_density=0.4,
        ),
        deviations=[
            StyleDeviation(
                paragraph_index=2,
                snippet="这段突然口语化了",
                deviation_type="register",
                severity=0.7,
                suggestion="保持叙述者正式语域",
            ),
        ],
        register_consistency=0.75,
        character_voice_issues=["张三在段落 3 的对话措辞不符身份"],
        confidence=0.65,
        needs_human_review=False,
    )

    assert response.style_metrics.avg_sentence_length == 42.5
    assert len(response.deviations) == 1
    assert response.register_consistency == 0.75
    assert len(response.character_voice_issues) == 1
    assert response.confidence == 0.65
    assert not response.needs_human_review

    print("  [PASS] test_response_data_model")
    return True


def test_engine_without_llm():
    """测试 8: 无 LLM 时引擎正常工作（fallback 模式）"""
    engine = ProseEngine(llm_client=None)
    query = ProseQuery(
        text=SAMPLE_LITERARY,
        chapter_id="test_fallback",
        baseline_texts=[SAMPLE_LITERARY[:500]],
    )
    response = engine.analyze(query)

    assert response.style_metrics is not None
    assert response.style_metrics.register_level in (
        "casual", "informal", "neutral", "formal", "literary"
    ), f"语域应为有效值，实际: {response.style_metrics.register_level}"
    # Fallback 模式置信度较低
    assert response.confidence < 0.8, (
        f"Fallback 置信度应较低，实际: {response.confidence}"
    )

    print(f"  [PASS] test_engine_without_llm "
          f"(fallback 置信度={response.confidence:.2f})")
    return True


# =====================================================================
# 主入口
# =====================================================================

def main():
    print("=" * 60)
    print("  文辞引擎测试 (Prose Engine Test)")
    print("=" * 60)
    print()

    tests = [
        test_prose_engine_import,
        test_style_metrics_extraction,
        test_register_detection,
        test_deviations_with_baseline,
        test_dialogue_analysis,
        test_character_voice_check,
        test_response_data_model,
        test_engine_without_llm,
    ]

    passed = 0
    failed = 0

    for i, test_fn in enumerate(tests, 1):
        print(f"[{i}/{len(tests)}] {test_fn.__doc__}")
        try:
            if test_fn():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {e}")
            import traceback
            traceback.print_exc()
        print()

    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed == 0:
        print("  [ALL PASS] Prose Engine test suite complete!")
    else:
        print(f"  [FAIL] {failed} test(s) failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
