"""
Narrative Mind API 服务器 — Phase 1

职责：提供 REST API 接口，连接前端和 Python 后端。
"""

import os
import sys
from pathlib import Path

# 可靠路径解析：支持开发模式 (python api_server.py) 和打包模式 (EXE)
if getattr(sys, 'frozen', False):
    # PyInstaller 打包模式 — 资源在临时目录
    _BASE = Path(sys._MEIPASS)
else:
    _BASE = Path(__file__).resolve().parent.parent

_PROJECT_ROOT = _BASE
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from src.corpus_anchor.slice_manager import SliceManager
from src.corpus_anchor.embedder import Embedder
from src.corpus_anchor.retriever import Retriever
from src.corpus_anchor.enricher import Enricher
from src.corpus_anchor.refiner import Refiner
from src.engines.character import CharacterEngine, CharacterQuery
from src.engines.world import WorldEngine, WorldQuery
from src.consistency_guardian.guardian import ConsistencyGuardian, GuardianInput
from src.orchestrator.router import Orchestrator, UserAction
from src.project_manager import ProjectManager, ProjectSettings as PSettings
from src.analysis_store import AnalysisStore
from src.llm import LLMClient, CostTracker, get_config
from src.llm.prompts import ENTITY_EXTRACT_SYSTEM, format_entity_extract_prompt

app = Flask(__name__, static_folder=None)
CORS(app)


def _to_json(obj):
    """将 Python 对象递归转换为 JSON 可序列化格式

    处理：dataclass → dict, Enum → value, list/dict 递归。
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_to_json(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _to_json(val) for key, val in obj.items()}
    if hasattr(obj, "value"):
        # Enum
        return obj.value
    if hasattr(obj, "__dataclass_fields__") or hasattr(obj, "__dict__"):
        result = {}
        for key, val in vars(obj).items():
            if not key.startswith("_"):
                result[key] = _to_json(val)
        return result
    # Fallback
    return str(obj)

# 初始化 LLM 客户端和成本追踪
llm_config = get_config()
cost_tracker = CostTracker()
llm_client = LLMClient(config=llm_config, cost_tracker=cost_tracker)

# 初始化语料自扩充器（默认项目 — 后续按 project_id 动态切换）
_enricher = Enricher(project_id="default")

# 初始化语料锚定层
slice_manager = SliceManager()
embedder = Embedder()
retriever = Retriever(
    embedder=embedder,
    slice_manager=slice_manager,
    similarity_threshold=0.1,
    llm_client=llm_client,
    enricher=_enricher,
)

# 加载语料
corpus_dir = str(_PROJECT_ROOT / "corpus")
slice_manager.load_slices(os.path.join(corpus_dir, "public-domain", "hong-lou-meng"))
slice_manager.load_slices(os.path.join(corpus_dir, "user"))

# 构建索引
retriever.build_index()

# 初始化引擎（传入 LLM 客户端）
character_engine = CharacterEngine(retriever=retriever, llm_client=llm_client)

world_engine = WorldEngine(llm_client=llm_client)
settings_path = str(_PROJECT_ROOT / "config" / "world-settings.json")
world_engine.load_settings(settings_path)
world_engine.load_character_power_levels({
    "贾宝玉": "普通人",
    "林黛玉": "普通人",
    "王熙凤": "普通人",
    "陈平安": "修行者",
    "路明非": "修行者",
})

guardian = ConsistencyGuardian()

# 初始化静态语料反哺器（Item 1: Refiner）
refiner = Refiner(slice_manager=slice_manager)

orchestrator = Orchestrator(
    character_engine=character_engine,
    world_engine=world_engine,
    guardian=guardian,
    enricher=_enricher,
    retriever=retriever,
    refiner=refiner,
)

# 项目管理 — 项目目录放在 EXE 旁边（可写），而非临时目录
if getattr(sys, 'frozen', False):
    _PROJECTS_DIR = Path(sys.executable).parent / "projects"
else:
    _PROJECTS_DIR = _PROJECT_ROOT / "projects"

project_manager = ProjectManager(str(_PROJECTS_DIR))

# 初始化分析历史存储
analysis_store = AnalysisStore(str(_PROJECTS_DIR))


# =========================================================================
# Project CRUD
# =========================================================================

@app.route('/api/projects', methods=['GET'])
def list_projects():
    """列出所有项目"""
    projects = project_manager.list_projects()
    return jsonify(_to_json(projects))


@app.route('/api/projects', methods=['POST'])
def create_project():
    """创建新项目"""
    data = request.json or {}
    name = data.get('name', '未命名项目')
    template = data.get('template_settings', None)
    project = project_manager.create_project(name, template)
    return jsonify(_to_json(project)), 201


@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """获取项目详情"""
    proj = project_manager.get_project(project_id)
    if proj is None:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify(proj)


@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    """删除项目"""
    ok = project_manager.delete_project(project_id)
    if not ok:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify({'deleted': True})


@app.route('/api/projects/<project_id>/settings', methods=['GET'])
def get_project_settings(project_id: str):
    """获取项目设定"""
    settings = project_manager.get_settings(project_id)
    if settings is None:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify(_to_json(settings))


@app.route('/api/projects/<project_id>/settings', methods=['PUT'])
def save_project_settings(project_id: str):
    """保存项目设定"""
    data = request.json or {}
    settings = PSettings(
        characters=data.get('characters', []),
        locations=data.get('locations', []),
        power_system=data.get('power_system', {}),
    )
    ok = project_manager.save_settings(project_id, settings)
    if not ok:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify(_to_json(settings))


# =========================================================================
# Chapter CRUD
# =========================================================================

@app.route('/api/projects/<project_id>/chapters', methods=['GET'])
def list_chapters(project_id: str):
    """列出项目章节"""
    chapters = project_manager.list_chapters(project_id)
    return jsonify(_to_json(chapters))


@app.route('/api/projects/<project_id>/chapters', methods=['POST'])
def create_chapter(project_id: str):
    """创建新章节"""
    data = request.json or {}
    title = data.get('title', '新章节')
    chapter = project_manager.create_chapter(project_id, title)
    if chapter is None:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify(_to_json(chapter)), 201


@app.route('/api/projects/<project_id>/chapters/<chapter_id>', methods=['PUT'])
def save_chapter(project_id: str, chapter_id: str):
    """保存章节"""
    data = request.json or {}
    title = data.get('title', '')
    text = data.get('text', '')
    ok = project_manager.save_chapter(project_id, chapter_id, title, text)
    if not ok:
        return jsonify({'error': 'Chapter not found'}), 404
    return jsonify({'saved': True})


@app.route('/api/projects/<project_id>/chapters/<chapter_id>', methods=['DELETE'])
def delete_chapter(project_id: str, chapter_id: str):
    """删除章节"""
    ok = project_manager.delete_chapter(project_id, chapter_id)
    if not ok:
        return jsonify({'error': 'Chapter not found'}), 404
    return jsonify({'deleted': True})


# =========================================================================
# Analysis history endpoints (Item 4)
# =========================================================================


@app.route('/api/projects/<project_id>/chapters/<chapter_id>/analysis', methods=['GET'])
def get_analysis_history(project_id: str, chapter_id: str):
    """获取章节的分析历史列表（不含完整 response body）"""
    history = analysis_store.get_history(project_id, chapter_id)
    return jsonify(history)


@app.route('/api/projects/<project_id>/chapters/<chapter_id>/analysis/<analysis_id>', methods=['GET'])
def get_analysis_detail(project_id: str, chapter_id: str, analysis_id: str):
    """获取单条分析详情（含完整 response body）"""
    detail = analysis_store.get_detail(project_id, chapter_id, analysis_id)
    if detail is None:
        return jsonify({'error': 'Analysis record not found'}), 404
    return jsonify(detail)


@app.route('/api/projects/<project_id>/chapters/<chapter_id>/analysis', methods=['POST'])
def save_analysis_record(project_id: str, chapter_id: str):
    """保存分析记录"""
    data = request.json or {}
    record = analysis_store.save(
        project_id=project_id,
        chapter_id=chapter_id,
        character_id=data.get('character_id', ''),
        location=data.get('location', ''),
        response=data.get('response', {}),
    )
    return jsonify(_to_json(record)), 201


# =========================================================================
# Entity suggestions endpoint (Item 2)
# =========================================================================


@app.route('/api/projects/<project_id>/suggestions/entities', methods=['POST'])
def suggest_entities(project_id: str):
    """从章节文本中自动提取角色和地点建议

    请求体：
        - chapter_text: str — 章节文本（优先使用）
        - chapter_id: str — 章节 ID（若未提供 chapter_text，则从项目加载）

    返回不在项目已知列表中的新实体建议。
    """
    data = request.json or {}

    # 获取章节文本
    chapter_text = data.get('chapter_text', '')
    if not chapter_text:
        chapter_id = data.get('chapter_id', '')
        if chapter_id:
            chapter = project_manager.get_chapter(project_id, chapter_id)
            if chapter:
                chapter_text = chapter.get('text', '')

    if not chapter_text or not chapter_text.strip():
        return jsonify({'error': 'No chapter text provided'}), 400

    # 检查 LLM 可用性
    if not llm_client.is_available:
        return jsonify({
            'error': 'LLM 不可用，无法进行实体提取',
            'suggestions': [],
            'known_characters': [],
            'known_locations': [],
            'llm_used': False,
        }), 503

    # 获取项目已知实体
    settings = project_manager.get_settings(project_id)
    known_characters = list(settings.characters) if settings else []
    known_locations = list(settings.locations) if settings else []

    # 调用 LLM 提取实体
    try:
        prompt = format_entity_extract_prompt(chapter_text)
        result = llm_client.call(
            system_prompt=ENTITY_EXTRACT_SYSTEM,
            user_prompt=prompt,
        )
    except Exception:
        return jsonify({
            'error': 'LLM 调用失败',
            'suggestions': [],
            'known_characters': known_characters,
            'known_locations': known_locations,
            'llm_used': False,
        }), 500

    # 解析 LLM 结果
    extracted_chars = result.get('characters', []) if isinstance(result, dict) else []
    extracted_locs = result.get('locations', []) if isinstance(result, dict) else []

    # 找出不在已知列表中的新实体
    known_chars_lower = {c.lower() for c in known_characters}
    known_locs_lower = {l.lower() for l in known_locations}

    suggestions = []

    for name in extracted_chars:
        if isinstance(name, str) and name.lower() not in known_chars_lower:
            # 提取上下文（原文中包含该名称的片段）
            context = _extract_context(chapter_text, name)
            suggestions.append({
                'name': name,
                'type': 'character',
                'context': context,
                'is_new': True,
            })

    for name in extracted_locs:
        if isinstance(name, str) and name.lower() not in known_locs_lower:
            context = _extract_context(chapter_text, name)
            suggestions.append({
                'name': name,
                'type': 'location',
                'context': context,
                'is_new': True,
            })

    return jsonify({
        'suggestions': suggestions,
        'known_characters': known_characters,
        'known_locations': known_locations,
        'llm_used': True,
    })


def _extract_context(text: str, entity_name: str, window: int = 20) -> str:
    """从文本中提取包含实体名称的上下文片段

    Args:
        text: 完整文本
        entity_name: 实体名称
        window: 前后窗口字符数

    Returns:
        上下文片段（含省略号标注）
    """
    pos = text.find(entity_name)
    if pos == -1:
        return f"…{entity_name}…"
    start = max(0, pos - window)
    end = min(len(text), pos + len(entity_name) + window)
    snippet = text[start:end]
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{snippet}{suffix}"


# =========================================================================
# Existing endpoints (with project support)
# =========================================================================


@app.route('/api/character/analyze', methods=['POST'])
def analyze_character():
    """分析角色"""
    data = request.json
    query = CharacterQuery(
        character_id=data.get('character_id', ''),
        scene_text=data.get('scene_text', ''),
    )
    result = character_engine.analyze(query)
    return jsonify(_to_json(result))


@app.route('/api/world/validate', methods=['POST'])
def validate_world():
    """校验世界规则"""
    data = request.json
    query = WorldQuery(
        event_description=data.get('event_description', ''),
        location=data.get('location', ''),
        involved_characters=data.get('involved_characters', []),
    )
    result = world_engine.validate(query)
    return jsonify(_to_json(result))


@app.route('/api/guardian/check', methods=['POST'])
def check_consistency():
    """一致性检查"""
    data = request.json
    input_data = GuardianInput(
        engine_results=data.get('engine_results', {}),
        active_dimensions=data.get('active_dimensions', ['character', 'world_rule', 'spatial']),
    )
    result = guardian.check(input_data)
    return jsonify(_to_json(result))


@app.route('/api/orchestrator/execute', methods=['POST'])
def execute_orchestrator():
    """执行编排器。支持 project_id 参数，使用项目专属设定。"""
    data = request.json
    project_id = data.get('project_id')

    # 如果提供了 project_id，加载项目专属设定
    if project_id:
        settings = project_manager.get_settings(project_id)
        if settings:
            # 动态加载项目角色力量等级
            char_levels = {name: "修行者" for name in settings.characters}
            world_engine.load_character_power_levels(char_levels)

    action = UserAction(
        type=data.get('type', 'analyze'),
        payload=data.get('payload', {}),
    )
    result = orchestrator.execute(action)
    serialized = _to_json(result)

    # 自动持久化分析结果（Item 4）
    if project_id:
        chapter_id = data.get('payload', {}).get('chapter_id', '')
        if chapter_id:
            try:
                analysis_store.save(
                    project_id=project_id,
                    chapter_id=chapter_id,
                    character_id=data.get('payload', {}).get('character_id', ''),
                    location=data.get('payload', {}).get('location', ''),
                    response=serialized,
                )
            except Exception:
                pass  # 持久化失败不影响主流程

    # 诊断日志
    cr = serialized.get('engine_results', {}).get('character_engine', {})
    print(f"[API] analyze: character={data.get('payload', {}).get('character_id', '?')}, "
          f"pad={cr.get('pad_state', 'MISSING')}, "
          f"confidence={cr.get('confidence', 'MISSING')}, "
          f"llm_ok={llm_client.is_available}")

    return jsonify(serialized)


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'slices_loaded': len(slice_manager.get_all_slices()),
        'vocabulary_size': embedder.vocabulary_size,
        'llm_available': llm_client.is_available,
        'llm_model': llm_config.model,
        **cost_tracker.status(),
        'enriched_slices_count': _enricher.dynamic_slice_count,
        'analysis_records': analysis_store.total_count(),
        'refinements_count': refiner.refinement_count,
    })


# =========================================================================
# Static file serving (for packaged/production mode)
# =========================================================================

_FRONTEND_DIR = _PROJECT_ROOT / "src" / "frontend" / "build"


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path: str):
    """Serve React frontend. Falls back to index.html for SPA routing."""
    if path:
        file_path = _FRONTEND_DIR / path
        if file_path.is_file():
            return send_file(file_path)
    return send_file(_FRONTEND_DIR / "index.html")


if __name__ == '__main__':
    import webbrowser
    import threading

    print("Starting Narrative Mind API server...")
    print(f"Loaded {len(slice_manager.get_all_slices())} slices")
    print(f"Vocabulary size: {embedder.vocabulary_size}")
    print(f"LLM available: {llm_client.is_available}")
    print(f"LLM model: {llm_config.model}")
    print(f"Enricher ready: {_enricher.dynamic_slice_count} dynamic slices")

    # Open browser after a short delay
    if _FRONTEND_DIR.exists():
        threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
        print("Frontend will be served at http://127.0.0.1:5000")
    else:
        print("Warning: Frontend not built. Run: cd src/frontend && npm run build")

    app.run(debug=False, port=5000)
