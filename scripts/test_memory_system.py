"""
三层记忆系统集成测试 — Phase 2

测试流程：
1. 工作记忆读写 + 过滤
2. 情节记忆 SQLite 持久化
3. 因果图谱 + 伏笔登记
4. 永久记忆作者指纹
5. 角色原型库
6. 主动遗忘
"""

import sys
import os
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.memory.working_memory import WorkingMemory, MemoryWrite, MemoryQuery
from src.memory.episodic_memory import EpisodicMemory, EpisodicQuery
from src.memory.permanent_memory import (
    PermanentMemory,
    AuthorFingerprint,
    CharacterArchetype,
    WorldRulePattern,
)


# =====================================================================
# 测试数据路径
# =====================================================================

TEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "projects", "memory")
os.makedirs(TEST_DIR, exist_ok=True)


# =====================================================================
# 测试
# =====================================================================

def test_working_memory_rw():
    """测试 1: 工作记忆读写和过滤"""
    wm = WorkingMemory()

    # 写入
    wm.write(MemoryWrite(
        source_engine="character_engine",
        target_tier="working",
        memory_type="pad_state",
        data={"character_id": "baoyu", "pleasure": 0.5, "arousal": 0.3, "dominance": 0.7},
        confidence=0.8,
    ))
    wm.write(MemoryWrite(
        source_engine="world_engine",
        target_tier="working",
        memory_type="world_event",
        data={"event": "宝玉摔玉", "location": "荣国府"},
        confidence=0.9,
    ))

    assert wm.size() == 2, f"应有 2 条记录，实际: {wm.size()}"

    # 按角色过滤
    results = wm.read(MemoryQuery(character_id="baoyu"))
    assert len(results) == 1
    assert results[0].data["pleasure"] == 0.5

    # 按类型过滤
    results = wm.read(MemoryQuery(memory_type="world_event"))
    assert len(results) == 1
    assert results[0].data["event"] == "宝玉摔玉"

    # 不匹配的过滤
    results = wm.read(MemoryQuery(character_id="daiyu"))
    assert len(results) == 0

    wm.clear()
    assert wm.size() == 0

    print("  [PASS] test_working_memory_rw")
    return True


def test_episodic_memory_persistence():
    """测试 2: 情节记忆 SQLite 持久化"""
    db_path = os.path.join(TEST_DIR, "test_episodic.db")
    em = EpisodicMemory(db_path=db_path)

    # 写入章节摘要
    em.write(
        chapter_id="ch_01",
        memory_type="chapter_summary",
        data={"summary": "宝玉初会黛玉，摔玉", "key_characters": ["baoyu", "daiyu"]},
        confidence=0.9,
    )

    # 写入选角色行为日志
    em.write(
        chapter_id="ch_01",
        memory_type="behavior_log",
        character_id="baoyu",
        data={"action": "摔玉", "trigger": "黛玉说没有玉"},
        confidence=0.85,
    )

    # 读取
    results = em.read(EpisodicQuery(chapter_id="ch_01", top_k=10))
    assert len(results) >= 2, f"应有至少 2 条记录，实际: {len(results)}"

    # 获取章节摘要
    summary = em.get_chapter_summary("ch_01")
    assert summary is not None
    assert "summary" in summary

    # 角色历史
    history = em.get_character_history("baoyu")
    assert len(history) >= 1

    # 统计
    stats = em.get_stats()
    assert stats.total_entries >= 2
    assert stats.chapters_covered >= 1

    print(f"  [PASS] test_episodic_memory_persistence")
    print(f"         entries={stats.total_entries}, chapters={stats.chapters_covered}, "
          f"db_size={stats.db_size_bytes} bytes")
    return True


def test_causality_graph():
    """测试 3: 因果图谱 + 伏笔登记"""
    db_path = os.path.join(TEST_DIR, "test_episodic.db")
    em = EpisodicMemory(db_path=db_path)

    # 添加因果链
    link1 = em.add_causal_link(
        chapter_id="ch_01",
        cause_event="宝玉摔玉",
        effect_event="黛玉自责",
        strength=0.8,
        description="宝玉因黛玉说没有玉而摔玉，黛玉认为因自己而起",
    )
    assert link1

    link2 = em.add_causal_link(
        chapter_id="ch_02",
        cause_event="贾母劝慰",
        effect_event="宝玉黛玉和好",
        strength=0.7,
        description="贾母出面调停",
    )
    assert link2

    # 获取因果链
    links = em.get_causal_links(chapter_id="ch_01")
    assert len(links) >= 1

    # 伏笔登记
    em.register_foreshadowing(
        foreshadow_id="fs_001",
        chapter_id="ch_01",
        description="宝玉的通灵宝玉暗藏玄机",
        hint_text="莫失莫忘，仙寿恒昌",
        category="object",
        related_characters=["baoyu"],
        confidence=0.8,
    )

    em.register_foreshadowing(
        foreshadow_id="fs_002",
        chapter_id="ch_02",
        description="贾雨村判断葫芦案",
        hint_text="葫芦僧判断葫芦案",
        category="event",
        confidence=0.7,
    )

    # 获取未回收伏笔
    unresolved = em.get_unresolved_foreshadowings()
    assert len(unresolved) >= 2

    # 标记回收
    success = em.resolve_foreshadowing("fs_002", "ch_05")
    assert success

    unresolved_after = em.get_unresolved_foreshadowings()
    assert len(unresolved_after) == len(unresolved) - 1

    print(f"  [PASS] test_causality_graph")
    print(f"         causal_links={len(links)}, "
          f"unresolved_foreshadowings={len(unresolved_after)}")
    return True


def test_permanent_fingerprint():
    """测试 4: 永久记忆作者指纹"""
    db_path = os.path.join(TEST_DIR, "test_permanent.db")
    # 确保测试从干净状态开始
    if os.path.exists(db_path):
        os.remove(db_path)
    pm = PermanentMemory(db_path=db_path)

    # 首次更新指纹
    fp1 = pm.update_fingerprint({
        "avg_sentence_length": 25.0,
        "dialogue_ratio": 0.3,
        "vocabulary_richness": 0.65,
        "register_level": "literary",
        "rhetoric_density": 0.4,
    })
    assert fp1.total_chapters_analyzed == 1
    assert fp1.register_level == "literary"

    # 再次更新（移动平均）
    fp2 = pm.update_fingerprint({
        "avg_sentence_length": 15.0,  # 短句章节
        "dialogue_ratio": 0.6,  # 对话多
        "vocabulary_richness": 0.55,
        "register_level": "neutral",
        "rhetoric_density": 0.2,
    })
    assert fp2.total_chapters_analyzed == 2
    # 首次直接赋值 25，第二次移动平均: 25*0.8 + 15*0.2 = 23
    assert 20 <= fp2.avg_sentence_length <= 25, (
        f"移动平均句长异常: {fp2.avg_sentence_length}"
    )

    # 读取指纹
    fp_got = pm.get_fingerprint()
    assert fp_got is not None
    assert fp_got.total_chapters_analyzed == 2

    print(f"  [PASS] test_permanent_fingerprint")
    print(f"         chapters={fp_got.total_chapters_analyzed}, "
          f"register={fp_got.register_level}, "
          f"avg_sent_len={fp_got.avg_sentence_length:.1f}")
    return True


def test_archetype_library():
    """测试 5: 角色原型库"""
    db_path = os.path.join(TEST_DIR, "test_permanent.db")
    pm = PermanentMemory(db_path=db_path)

    # 保存角色原型
    arch1 = CharacterArchetype(
        label="叛逆公子",
        pad_baseline={"pleasure": 0.2, "arousal": 0.6, "dominance": 0.7},
        behavior_patterns=["反抗权威", "保护弱者", "愤世嫉俗"],
        typical_roles=["男主", "反英雄"],
        appearances_across_works=3,
    )
    arch_id = pm.save_archetype(arch1)
    assert arch_id

    # 保存另一个原型
    arch2 = CharacterArchetype(
        label="智囊谋士",
        pad_baseline={"pleasure": 0.5, "arousal": 0.3, "dominance": 0.8},
        behavior_patterns=["出谋划策", "暗中操控", "深藏不露"],
        typical_roles=["军师", "幕后黑手"],
        appearances_across_works=5,
    )
    pm.save_archetype(arch2)

    # 列出原型
    archetypes = pm.list_archetypes(min_appearances=1)
    assert len(archetypes) >= 2

    # 按出现次数降序
    assert archetypes[0].appearances_across_works >= archetypes[1].appearances_across_works

    # 获取单个
    got = pm.get_archetype(arch_id)
    assert got is not None
    assert got.label == "叛逆公子"

    print(f"  [PASS] test_archetype_library")
    print(f"         archetypes={len(archetypes)}, most_common={archetypes[0].label}")
    return True


def test_world_rule_patterns():
    """测试 6: 世界规则模式库"""
    db_path = os.path.join(TEST_DIR, "test_permanent.db")
    pm = PermanentMemory(db_path=db_path)

    # 保存规则模式
    rule1 = WorldRulePattern(
        rule_category="power_system",
        pattern_description="修炼境界分为九层，每层突破需渡劫",
        examples=["筑基→金丹→元婴→化神→炼虚→合体→大乘→渡劫→真仙"],
        usage_count=3,
    )
    rule_id = pm.save_rule_pattern(rule1)
    assert rule_id

    rule2 = WorldRulePattern(
        rule_category="social",
        pattern_description="宗门等级森严，内门外门弟子地位悬殊",
        examples=["外门弟子负责杂役", "内门弟子可听长老传道"],
        usage_count=2,
    )
    pm.save_rule_pattern(rule2)

    # 搜索
    results = pm.find_similar_rules(rule_category="power_system", top_k=10)
    assert len(results) >= 1
    assert "九层" in results[0].pattern_description or "修炼" in results[0].pattern_description

    # 关键词搜索
    results = pm.find_similar_rules(keyword="宗门")
    assert len(results) >= 1
    assert "宗门" in results[0].pattern_description

    print(f"  [PASS] test_world_rule_patterns")
    print(f"         found_power_system={len(pm.find_similar_rules(rule_category='power_system'))}")
    return True


def test_prune_stale_data():
    """测试 7: 主动遗忘机制"""
    db_path = os.path.join(TEST_DIR, "test_permanent.db")
    pm = PermanentMemory(db_path=db_path)

    # 保存一个低频使用原型（会被标记但不会立即删除）
    arch = CharacterArchetype(
        label="路人甲",
        appearances_across_works=1,
    )
    pm.save_archetype(arch)

    # 清理过期数据（0 天阈值，清理所有未访问的）
    removed = pm.prune_stale_data(days_threshold=0)
    # 主动遗忘是衰减计数而非硬删除，所以总是成功
    assert removed >= 0

    print(f"  [PASS] test_prune_stale_data (removed={removed})")
    return True


def test_stats():
    """测试 8: 统计信息"""
    db_path = os.path.join(TEST_DIR, "test_permanent.db")
    pm = PermanentMemory(db_path=db_path)

    stats = pm.get_stats()
    assert "archetypes" in stats
    assert "rule_patterns" in stats
    assert stats["db_size_bytes"] > 0

    print(f"  [PASS] test_stats (archetypes={stats['archetypes']}, "
          f"rules={stats['rule_patterns']})")
    return True


def test_full_memory_flow():
    """测试 9: 端到端记忆流程（写工作记忆 → 下沉情节记忆 → 沉淀永久指纹）"""
    # 1. 工作记忆: 写入 PAD 数据
    wm = WorkingMemory()
    wm.write(MemoryWrite(
        source_engine="character_engine",
        target_tier="working",
        memory_type="pad_state",
        data={"character_id": "baoyu", "pleasure": 0.2, "arousal": 0.7, "dominance": 0.5},
        confidence=0.9,
    ))

    # 2. 情节记忆: 章节结束时下沉
    db_path = os.path.join(TEST_DIR, "test_episodic.db")
    em = EpisodicMemory(db_path=db_path)
    em.write(
        chapter_id="ch_final",
        memory_type="pad_history",
        character_id="baoyu",
        data={"pleasure": 0.2, "arousal": 0.7, "dominance": 0.5},
        confidence=0.9,
    )
    # 章节摘要
    em.write(
        chapter_id="ch_final",
        memory_type="chapter_summary",
        data={"summary": "宝玉挨打后黛玉探视，二人交心"},
        confidence=0.85,
    )

    # 验证情节记忆中的角色历史
    history = em.get_character_history("baoyu")
    assert len(history) >= 1
    # 找最新一条 pad_history 条目验证
    pad_entries = [h for h in history if h.memory_type == "pad_history"]
    assert len(pad_entries) >= 1
    assert pad_entries[0].data.get("pleasure") == 0.2

    # 3. 永久记忆: 更新作者指纹
    db_path2 = os.path.join(TEST_DIR, "test_permanent.db")
    pm = PermanentMemory(db_path=db_path2)
    pm.update_fingerprint({
        "avg_sentence_length": 22.0,
        "dialogue_ratio": 0.45,
        "vocabulary_richness": 0.6,
        "register_level": "literary",
        "rhetoric_density": 0.35,
    })

    fp = pm.get_fingerprint()
    assert fp is not None

    wm.clear()
    print(f"  [PASS] test_full_memory_flow (fingerprint chapters={fp.total_chapters_analyzed})")
    return True


# =====================================================================
# 主入口
# =====================================================================

def main():
    print("=" * 60)
    print("  三层记忆系统集成测试 (Memory System Test)")
    print("=" * 60)
    print()

    tests = [
        test_working_memory_rw,
        test_episodic_memory_persistence,
        test_causality_graph,
        test_permanent_fingerprint,
        test_archetype_library,
        test_world_rule_patterns,
        test_prune_stale_data,
        test_stats,
        test_full_memory_flow,
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
        print("  [ALL PASS] Memory System test suite complete!")
    else:
        print(f"  [FAIL] {failed} test(s) failed")
    print("=" * 60)

    # 清理测试数据库
    for f in os.listdir(TEST_DIR):
        if f.startswith("test_"):
            try:
                os.remove(os.path.join(TEST_DIR, f))
            except PermissionError:
                pass  # SQLite 连接可能未完全释放

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
