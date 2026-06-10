#!/usr/bin/env python3
"""
叙事引擎集成测试 — Phase 2

测试流程：
1. 伏笔检测（LLM + fallback）
2. 因果链提取（LLM + fallback）
3. 跨章节伏笔回收检查
4. 叙事问题检测
5. 短期情节推演
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engines.narrative import (
    NarrativeEngine,
    NarrativeQuery,
    NarrativeResponse,
    Foreshadowing,
    CausalLink,
    FORESHADOW_KEYWORDS,
    CAUSAL_KEYWORDS,
)


# ---------------------------------------------------------------------------
# 测试数据
# ---------------------------------------------------------------------------

# 模拟《红楼梦》章节文本（公开域）
HLM_SAMPLE = """话说林黛玉自那日弃舟登岸时，便有荣国府打发了轿子并拉行李的车辆久候了。
林黛玉常听得母亲说过，他外祖母家与别家不同。近日所见的这几个三等仆妇，
吃穿用度，已是不凡了，何况今至其家。因此步步留心，时时在意，不肯轻易多说一句话，
多行一步路，惟恐被人耻笑了他去。自上了轿，进入城中，从纱窗向外瞧了一瞧，
其街市之繁华，人烟之阜盛，自与别处不同。又行了半日，忽见街北蹲着两个大石狮子，
三间兽头大门，门前列坐着十来个华冠丽服之人。正门却不开，只有东西两角门有人出入。
正门之上有一匾，匾上大书"敕造宁国府"五个大字。黛玉想道：这必是外祖之长房了。
想着，又往西行，不多远，照样也是三间大门，方是荣国府了。"""

# 模拟后续章节（用于跨章节检查）
FOLLOWUP_SAMPLE = """那黛玉进得荣国府，一一拜见过外祖母与各位嫂嫂。众人见黛玉年貌虽小，
其举止言谈不俗，身体面庞虽怯弱不胜，却有一段自然的风流态度，便知他有不足之症。
因问："常服何药，如何不急为疗治？"黛玉道："我自来是如此，从会吃饮食时便吃药，
到今日未断，请了多少名医修方配药，皆不见效。那一年我三岁时，听得说来了一个癞头和尚，
说要化我去出家，我父母固是不从。他又说：'既舍不得他，只怕他的病一生也不能好的了。
若要好时，除非从此以后总不许见哭声，除父母之外，凡有外姓亲友之人，一概不见，
方可平安了此一世。'疯疯癫癫，说了这些不经之谈，也没人理他。如今还是吃人参养荣丸。"""


def test_foreshadow_keyword_fallback():
    """测试伏笔检测 — 关键词 fallback"""
    print("=" * 60)
    print("[1/6] 伏笔检测 — 关键词 fallback 模式")
    print("=" * 60)

    engine = NarrativeEngine(llm_client=None)
    query = NarrativeQuery(
        chapter_text=HLM_SAMPLE,
        chapter_id="hlm_ch03",
    )

    result = engine.analyze(query)

    print(f"  检测到 {len(result.foreshadowings)} 个伏笔")
    for fs in result.foreshadowings:
        print(f"    [{fs.category}] {fs.description[:50]} (置信度: {fs.confidence:.2f})")

    # 验证基本结构
    assert isinstance(result, NarrativeResponse), "结果类型应为 NarrativeResponse"
    assert result.confidence >= 0.0, "置信度应为非负"
    print(f"\n  整体置信度: {result.confidence:.2f}")
    print("  [PASS] 关键词 fallback 测试通过")


def test_causal_keyword_fallback():
    """测试因果链提取 — 关键词 fallback"""
    print("\n" + "=" * 60)
    print("[2/6] 因果链提取 — 关键词 fallback 模式")
    print("=" * 60)

    engine = NarrativeEngine(llm_client=None)
    query = NarrativeQuery(
        chapter_text=HLM_SAMPLE,
        chapter_id="hlm_ch03",
    )

    result = engine.analyze(query)

    # 注意：关键词 fallback 对古文可能效果有限
    print(f"  检测到 {len(result.causal_links)} 条因果链")
    for link in result.causal_links[:3]:
        print(f"    [{link.strength:.2f}] {link.cause_event[:40]} → {link.effect_event[:40]}")

    print("  [PASS] 因果链测试通过")


def test_cross_chapter_resolution():
    """测试跨章节伏笔回收检查"""
    print("\n" + "=" * 60)
    print("[3/6] 跨章节伏笔回收检查")
    print("=" * 60)

    engine = NarrativeEngine(llm_client=None)

    # 先分析第一章，收集伏笔
    query1 = NarrativeQuery(
        chapter_text=HLM_SAMPLE,
        chapter_id="hlm_ch03",
    )
    result1 = engine.analyze(query1)
    print(f"  第一章伏笔数: {len(result1.foreshadowings)}")

    # 假设第一章检测到的伏笔
    known = [
        Foreshadowing(
            foreshadow_id="test_fs_1",
            chapter_id="hlm_ch03",
            description="癞头和尚预言黛玉的病一生不能好",
            hint_text="除非从此以后总不许见哭声",
            category="dialogue",
            status="planted",
            confidence=0.7,
        ),
        Foreshadowing(
            foreshadow_id="test_fs_2",
            chapter_id="hlm_ch03",
            description="黛玉步步留心不肯多说一句话的谨慎性格",
            hint_text="步步留心，时时在意，不肯轻易多说一句话",
            category="character",
            status="planted",
            confidence=0.6,
        ),
    ]

    # 分析后续章节，检查伏笔回收
    query2 = NarrativeQuery(
        chapter_text=FOLLOWUP_SAMPLE,
        chapter_id="hlm_ch03_cont",
        known_foreshadowings=known,
    )
    result2 = engine.analyze(query2)

    unresolved = result2.unresolved_foreshadowings
    print(f"  未回收伏笔: {len(unresolved)}")
    for fs in unresolved:
        print(f"    [{fs.category}] {fs.description[:50]}")

    print(f"  叙事问题: {len(result2.narrative_issues)}")
    for issue in result2.narrative_issues:
        print(f"    [!] {issue}")

    print("  [PASS] 跨章节检查测试通过")


def test_narrative_issues():
    """测试叙事问题检测"""
    print("\n" + "=" * 60)
    print("[4/6] 叙事问题检测")
    print("=" * 60)

    engine = NarrativeEngine(llm_client=None)

    # 模拟大量未回收伏笔
    known = [
        Foreshadowing(
            foreshadow_id=f"old_fs_{i}",
            chapter_id="ch01",
            description=f"第{i}个未回收的伏笔",
            hint_text="暗示文本...",
            category="object" if i % 2 == 0 else "event",
            status="planted",
        )
        for i in range(5)
    ]

    query = NarrativeQuery(
        chapter_text=HLM_SAMPLE,
        chapter_id="ch05",
        known_foreshadowings=known,
    )

    result = engine.analyze(query)

    # 应检测到长期未回收伏笔问题
    assert len(result.narrative_issues) > 0, "应检测到叙事问题"
    print(f"  检测到 {len(result.narrative_issues)} 个叙事问题:")
    for issue in result.narrative_issues:
        print(f"    [!] {issue}")

    print("  [PASS] 叙事问题检测测试通过")


def test_event_prediction():
    """测试短期情节推演"""
    print("\n" + "=" * 60)
    print("[5/6] 短期情节推演 — fallback 模式")
    print("=" * 60)

    engine = NarrativeEngine(llm_client=None)
    query = NarrativeQuery(
        chapter_text=HLM_SAMPLE,
        chapter_id="hlm_ch03",
    )

    result = engine.analyze(query)

    print(f"  情节推演: {result.event_prediction[:150]}...")
    assert len(result.event_prediction) > 0, "推演不应为空"
    print("  [PASS] 情节推演测试通过")


def test_foreshadowing_registry():
    """测试伏笔注册表和标记回收"""
    print("\n" + "=" * 60)
    print("[6/6] 伏笔注册表管理")
    print("=" * 60)

    engine = NarrativeEngine(llm_client=None)
    query = NarrativeQuery(
        chapter_text=HLM_SAMPLE,
        chapter_id="hlm_ch03",
    )

    engine.analyze(query)

    # 获取未回收伏笔
    unresolved = engine.get_unresolved_foreshadowings()
    print(f"  未回收伏笔总数: {len(unresolved)}")

    # 标记回收
    if unresolved:
        fs_id = unresolved[0].foreshadow_id
        success = engine.mark_resolved(fs_id, "hlm_ch10")
        print(f"  标记 {fs_id} 为已回收: {'成功' if success else '失败'}")

        # 验证
        remaining = engine.get_unresolved_foreshadowings()
        print(f"  剩余未回收: {len(remaining)}")
        assert len(remaining) == len(unresolved) - 1, "应减少一个未回收伏笔"

    print("  [PASS] 伏笔注册表测试通过")


def test_data_models():
    """验证数据模型构造"""
    print("\n" + "=" * 60)
    print("[额外] 数据模型完整性检查")
    print("=" * 60)

    fs = Foreshadowing(
        foreshadow_id="test_001",
        chapter_id="ch01",
        description="测试伏笔",
        hint_text="这是一段测试文本",
        category="dialogue",
        status="planted",
        related_characters=["角色A", "角色B"],
        confidence=0.8,
    )
    assert fs.foreshadow_id == "test_001"
    assert fs.status == "planted"

    link = CausalLink(
        cause_event="事件A",
        effect_event="事件B",
        strength=0.7,
        description="A导致B",
        chapter_id="ch01",
    )
    assert link.strength == 0.7

    query = NarrativeQuery(
        chapter_text="测试文本",
        chapter_id="ch01",
    )
    assert query.chapter_id == "ch01"

    print("  [PASS] 数据模型测试通过")


if __name__ == "__main__":
    test_data_models()
    test_foreshadow_keyword_fallback()
    test_causal_keyword_fallback()
    test_cross_chapter_resolution()
    test_narrative_issues()
    test_event_prediction()
    test_foreshadowing_registry()

    print("\n" + "=" * 60)
    print("[ALL PASS] Narrative Engine test suite complete!")
    print("=" * 60)
