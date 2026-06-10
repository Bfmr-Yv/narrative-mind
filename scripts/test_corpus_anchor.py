#!/usr/bin/env python3
"""
语料锚定层集成测试

测试流程：
1. 加载切片
2. 构建向量索引
3. 执行检索
4. 验证结果
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.corpus_anchor.slice_manager import SliceManager
from src.corpus_anchor.embedder import Embedder
from src.corpus_anchor.retriever import Retriever


def test_basic_flow():
    """测试基本流程"""
    print("=" * 60)
    print("语料锚定层集成测试")
    print("=" * 60)

    # 1. 初始化组件
    print("\n[1/4] 初始化组件...")
    slice_manager = SliceManager()
    embedder = Embedder()
    retriever = Retriever(embedder=embedder, slice_manager=slice_manager)

    # 2. 加载切片
    print("\n[2/4] 加载切片...")
    corpus_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpus")
    
    # 加载红楼梦切片
    hlm_dir = os.path.join(corpus_dir, "public-domain", "hong-lou-meng")
    hlm_count = slice_manager.load_slices(hlm_dir)
    print(f"  红楼梦切片: {hlm_count} 个")

    # 加载用户切片（如有）
    user_dir = os.path.join(corpus_dir, "user")
    user_count = slice_manager.load_slices(user_dir)
    print(f"  用户切片: {user_count} 个")

    total_slices = slice_manager.get_all_slices()
    print(f"  总计: {len(total_slices)} 个切片")

    # 3. 构建索引
    print("\n[3/4] 构建向量索引...")
    retriever.build_index()
    print(f"  索引完成，词汇表大小: {embedder.vocabulary_size}")
    print(f"  已索引切片: {retriever.slice_count}")

    # 4. 执行检索测试
    print("\n[4/4] 执行检索测试...")
    test_queries = [
        ("林黛玉初见贾宝玉", "scene"),
        ("王熙凤出场", "behavior"),
        ("刘姥姥进大观园", "scene"),
    ]

    for query_text, category in test_queries:
        print(f"\n  查询: '{query_text}' (类别: {category})")
        try:
            response = retriever.retrieve(query_text, category=category, top_k=3)
            if response.hits:
                for i, (hit, score) in enumerate(zip(response.hits, response.similarity_scores)):
                    print(f"    [{i+1}] {hit.slice_id} (相似度: {score:.4f})")
                    print(f"        来源: {hit.metadata.get('source', 'N/A')} - {hit.metadata.get('chapter', 'N/A')}")
                    print(f"        文本: {hit.text[:50]}...")
            else:
                print("    无结果（相似度均低于 0.3 阈值）")
        except Exception as e:
            print(f"    错误: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


def test_character_filter():
    """测试按角色过滤"""
    print("\n" + "=" * 60)
    print("角色过滤测试")
    print("=" * 60)

    # 初始化
    slice_manager = SliceManager()
    embedder = Embedder()
    retriever = Retriever(embedder=embedder, slice_manager=slice_manager)

    # 加载切片（仅公版语料）
    corpus_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpus")
    slice_manager.load_slices(os.path.join(corpus_dir, "public-domain", "hong-lou-meng"))
    # user 目录为空时安全跳过
    user_dir = os.path.join(corpus_dir, "user")
    if os.path.isdir(user_dir):
        slice_manager.load_slices(user_dir)

    # 构建索引
    retriever.build_index()

    # 测试按角色过滤
    test_cases = [
        ("贾宝玉", "林黛玉相关场景"),
        ("王熙凤", "凤姐相关场景"),
    ]

    for character_id, desc in test_cases:
        print(f"\n  角色: {character_id} ({desc})")
        try:
            response = retriever.retrieve_by_character(
                query_text=character_id,
                character_id=character_id,
                category="behavior",
                top_k=2
            )
            if response.hits:
                for i, (hit, score) in enumerate(zip(response.hits, response.similarity_scores)):
                    print(f"    [{i+1}] {hit.slice_id} (相似度: {score:.4f})")
            else:
                print("    无结果")
        except Exception as e:
            print(f"    错误: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_basic_flow()
    test_character_filter()
