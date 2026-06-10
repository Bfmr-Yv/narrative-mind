"""直接测试 API 请求 — 使用 requests 或 urllib"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Step 1: 测试项目列表
print("=== 1. 测试项目列表 ===")
from src.project_manager import ProjectManager
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PROJECTS_DIR = _PROJECT_ROOT / "projects"
pm = ProjectManager(str(_PROJECTS_DIR))
projects = pm.list_projects()
for p in projects:
    print(f"  项目: {p.id} | {p.name} | {p.chapter_count}章节 | {p.total_words}字")

# Step 2: 测试项目章节
if projects:
    proj = projects[0]
    print(f"\n=== 2. 测试章节列表 ({proj.id}) ===")
    chapters = pm.list_chapters(proj.id)
    print(f"  章节数: {len(chapters)}")
    for c in chapters:
        print(f"  - {c.id}: '{c.title}' ({len(c.text)}字)")

    # Step 3: 测试创建章节
    print(f"\n=== 3. 测试创建章节 ===")
    if not chapters:
        new_ch = pm.create_chapter(proj.id, "测试章节")
        if new_ch:
            print(f"  创建成功: {new_ch.id}")
            # 写入一些内容
            ok = pm.save_chapter(proj.id, new_ch.id, "测试章节", "贾宝玉在大观园中散步，见花开花落，心生感慨。")
            print(f"  保存成功: {ok}")
            # 读取验证
            saved = pm.get_chapter(proj.id, new_ch.id)
            if saved:
                print(f"  读取验证: '{saved.title}' ({len(saved.text)}字) text='{saved.text[:50]}...'")
            # 清理
            pm.delete_chapter(proj.id, new_ch.id)
            print(f"  已清理测试章节")
        else:
            print(f"  创建失败! project_id={proj.id}")

# Step 4: 测试 orchestrator API 请求（模拟 HTTP）
print(f"\n=== 4. 测试 orchestrator execute ===")
from src.api_server import app
with app.test_client() as client:
    resp = client.post('/api/orchestrator/execute', json={
        'type': 'analyze',
        'payload': {
            'character_id': '贾宝玉',
            'scene_text': '贾宝玉在大观园中散步，见花开花落，心生感慨。',
            'event_description': '贾宝玉在大观园中散步',
            'location': '大观园',
            'involved_characters': ['贾宝玉'],
        },
    })
    data = resp.get_json()
    print(f"  HTTP status: {resp.status_code}")
    print(f"  success: {data.get('success')}")
    cr = data.get('engine_results', {}).get('character_engine', {})
    print(f"  PAD: {cr.get('pad_state')}")
    print(f"  behavior: {cr.get('behavior_prediction', {}).get('predicted_action')}")
    print(f"  confidence: {cr.get('confidence')}")
    print(f"  needs_human_review: {cr.get('needs_human_review')}")
    if cr.get('pad_state', {}).get('pleasure', 0) == 0 and cr.get('pad_state', {}).get('arousal', 0) == 0:
        print("  ⚠️ PAD 全零！LLM 可能未生效")

print("\n=== DONE ===")
