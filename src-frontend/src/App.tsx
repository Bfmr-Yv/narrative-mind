/**
 * Narrative Mind v4.0 — 主应用组件
 *
 * Phase E: Monaco Editor + Agent 标注 + 分析面板 + 状态栏
 * Phase K: 分析结果迁移到 Zustand store，AnalysisPanel 改为结果浏览器
 */

import { useState, useCallback, useEffect } from "react";
import { Editor, StatusBar, StickyBoard, LibraryPanel, ProjectSettingsPanel, ImportPanel, ContextSuggestionsPanel, GoldenThreeWizard } from "./components";
import { createChapter as apiCreateChapter, updateChapter, deleteChapter, runAnalysis, runContinuation, onAgentProgress, onProposalReady, onAnalysisComplete, setSuggestionState, getDismissedSuggestions, clearDismissedSuggestions } from "./api";
import type { ChapterData, AnalysisComplete } from "./api";
import type { ProposalReady } from "./api/events";
import type { AgentState, AgentAnnotation, ProjectContext, ContextSuggestion } from "./types";
import { useAppStore } from "./store";
import "./App.css";

function App() {
  // ── Zustand store ──
  const storeAnalysisResult = useAppStore((s) => s.analysisResult);
  const storeAnalyzing = useAppStore((s) => s.analyzing);
  const setAnalysisResult = useAppStore((s) => s.setAnalysisResult);
  const setAnalyzing = useAppStore((s) => s.setAnalyzing);
  const projectContext = useAppStore((s) => s.projectContext);
  const loadProjectContext = useAppStore((s) => s.loadProjectContext);
  const saveProjectContext = useAppStore((s) => s.saveProjectContext);
  // TG-2: 从 store 读取项目/章节列表
  const projects = useAppStore((s) => s.projects);
  const chapters = useAppStore((s) => s.chapters);
  const storeLoadProjects = useAppStore((s) => s.loadProjects);
  const storeLoadChapters = useAppStore((s) => s.loadChapters);
  const storeCreateProject = useAppStore((s) => s.createProject);
  const storeCreateChapter = useAppStore((s) => s.createChapter);
  const storeUpdateChapter = useAppStore((s) => s.updateChapter);
  const storeDeleteChapter = useAppStore((s) => s.deleteChapter);

  // ── 本地状态 ──
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [selectedChapter, setSelectedChapter] = useState<ChapterData | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [annotations, setAnnotations] = useState<AgentAnnotation[]>([]);
  const [proposals, setProposals] = useState<ProposalReady[]>([]);
  const [agentStates, setAgentStates] = useState<AgentState[]>([]);
  const [totalCost, setTotalCost] = useState(0);
  const [viewMode, setViewMode] = useState<"editor" | "settings" | "import" | "golden">("editor");
  const [showNewProject, setShowNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [dismissedFindingIds, setDismissedFindingIds] = useState<Set<string>>(new Set());
  const [showContextSuggestions, setShowContextSuggestions] = useState(false);
  const [contextSuggestions, setContextSuggestions] = useState<ContextSuggestion[]>([]);
  const [continuationPending, setContinuationPending] = useState<string | null>(null);
  const [continuationCost, setContinuationCost] = useState(0);
  const [continuing, setContinuing] = useState(false);

  // ── 启动连通性检查 ──
  useEffect(() => {
    import("@tauri-apps/api/core").then(({ invoke }) => {
      invoke<[boolean, boolean, string]>("health_check").then(([ok, configured, model]) => {
        console.log(`[Narrative Mind] Backend OK=${ok} LLM=${configured} model=${model}`);
      }).catch(console.warn);
    });
  }, []);

  // ── 加载项目列表 ──
  useEffect(() => {
    storeLoadProjects().catch(console.error);
  }, [storeLoadProjects]);

  // ── 加载章节列表 ──
  useEffect(() => {
    if (selectedProject) {
      // 同步 currentProject 到 store（store actions 依赖它）
      const projectMeta = projects.find(p => p.id === selectedProject);
      if (projectMeta) {
        useAppStore.setState({ currentProject: projectMeta });
      }
      storeLoadChapters().catch(console.error);
    }
  }, [selectedProject, projects, storeLoadChapters]);

  // ── 事件监听 ──
  useEffect(() => {
    const unlisten1 = onAgentProgress((p) => {
      setAgentStates((prev) => {
        const idx = prev.findIndex((a) => a.agent_id === p.agent_id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = {
            ...next[idx],
            status: "running",
            progress: p.progress_pct,
          };
          return next;
        }
        return [
          ...prev,
          {
            agent_id: p.agent_id,
            agent_name: p.agent_name,
            status: "running",
            progress: p.progress_pct,
          },
        ];
      });
    });

    const unlisten2 = onProposalReady((p) => {
      setProposals((prev) => [...prev, p]);
    });

    const unlisten3 = onAnalysisComplete((evt: AnalysisComplete) => {
      // 标记所有 Agent 为完成
      setAgentStates((prev) =>
        prev.map((a) => (a.status === "running" ? { ...a, status: "done", progress: 100 } : a))
      );
      setTotalCost((prev) => prev + evt.total_cost);
      setAnalyzing(false);
    });

    return () => {
      unlisten1.then((fn) => fn());
      unlisten2.then((fn) => fn());
      unlisten3.then((fn) => fn());
    };
  }, [setAnalyzing]);

  // ── 章节选择 ──
  const handleSelectChapter = useCallback((ch: ChapterData) => {
    setSelectedChapter(ch);
    setEditorContent(ch.text);
    setAnnotations([]);
    setProposals([]);
    setAgentStates([]);
    setViewMode("editor");
  }, []);

  // ── 新建项目（inline 输入框，替换 prompt） ──
  const handleNewProject = useCallback(async () => {
    if (!newProjectName.trim()) return;
    try {
      const p = await storeCreateProject(newProjectName.trim());
      setSelectedProject(p.id);
      setNewProjectName("");
      setShowNewProject(false);
      // 加载 ProjectContext → 自动打开项目设置
      setTimeout(() => {
        loadProjectContext();
        setViewMode("settings");
      }, 100);
    } catch (e) {
      alert(`创建项目失败: ${e}`);
    }
  }, [newProjectName, loadProjectContext, storeCreateProject]);

  // ── 新建章节 ──
  const handleNewChapter = useCallback(async () => {
    if (!selectedProject) return;
    const title = prompt("章节标题：");
    if (!title?.trim()) return;
    try {
      const ch = await storeCreateChapter(title.trim(), "");
      setSelectedChapter(ch);
      setEditorContent(ch.text);
    } catch (e) {
      alert(`创建章节失败: ${e}`);
    }
  }, [selectedProject, storeCreateChapter]);

  // ── 删除章节 ──
  const handleDeleteChapter = useCallback(
    async (ch: ChapterData) => {
      if (!confirm(`删除章节 "${ch.title}"？`)) return;
      try {
        await storeDeleteChapter(ch.id);
        if (selectedChapter?.id === ch.id) {
          setSelectedChapter(null);
          setEditorContent("");
          setAnnotations([]);
          setProposals([]);
        }
      } catch (e) {
        alert(`删除章节失败: ${e}`);
      }
    },
    [selectedChapter, storeDeleteChapter]
  );

  // ── 保存 ──
  const handleSave = useCallback(async () => {
    if (!selectedChapter) return;
    const updated = { ...selectedChapter, text: editorContent };
    try {
      await storeUpdateChapter(updated);
      // 从 store 读取最新状态
      const latestChapters = useAppStore.getState().chapters;
      const saved = latestChapters.find(c => c.id === updated.id);
      if (saved) setSelectedChapter(saved);
    } catch (e) {
      alert(`保存失败: ${e}`);
    }
  }, [selectedChapter, editorContent, storeUpdateChapter]);

  // ── Ctrl+S ──
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleSave]);

  // ── 分析结果 → 标注映射 ──
  const applyAnnotations = useCallback((result: typeof storeAnalysisResult) => {
    if (!result?.findings) return;
    const newAnnotations: AgentAnnotation[] = result.findings.map((f) => ({
      id: `${result.request_id}-${f.agent_id}-${f.title}`,
      agent_id: f.agent_id,
      agent_name: f.agent_id,
      message: `${f.title}: ${f.description}`.substring(0, 200),
      severity: f.severity,
      location: f.location
        ? {
            start_line: f.location.start_line,
            start_column: f.location.start_column,
            end_line: f.location.end_line,
            end_column: f.location.end_column,
          }
        : undefined,
      suggestion: f.suggestion ?? undefined,
    }));
    setAnnotations(newAnnotations);
  }, []);

  // ── 快捷分析 ──
  const handleQuickAnalyze = useCallback(async () => {
    if (!selectedChapter || storeAnalyzing) return;
    setAnalyzing(true);
    setAnnotations([]);
    setProposals([]);
    setAgentStates([]);
    setContextSuggestions([]);
    try {
      // 加载已忽略的建议
      const dismissed = await getDismissedSuggestions(selectedProject, "finding");
      setDismissedFindingIds(new Set(dismissed));

      const result = await runAnalysis(selectedChapter.id, "scene_analysis");
      setAnalysisResult(result);
      applyAnnotations(result);
      setContextSuggestions(result.context_suggestions ?? []);
    } catch (e) {
      alert(`分析失败: ${e}`);
      setAnalyzing(false);
    }
  }, [selectedChapter, storeAnalyzing, selectedProject, setAnalyzing, setAnalysisResult, applyAnnotations]);

  // ── 建议管理 ──
  const handleDismissFinding = useCallback(async (id: string) => {
    if (!selectedProject || !selectedChapter) return;
    await setSuggestionState(id, selectedProject, selectedChapter.id, "finding", "dismissed");
    setDismissedFindingIds(prev => new Set(prev).add(id));
  }, [selectedProject, selectedChapter]);

  const handleSnoozeFinding = useCallback(async (id: string) => {
    if (!selectedProject || !selectedChapter) return;
    await setSuggestionState(id, selectedProject, selectedChapter.id, "finding", "snoozed");
    setDismissedFindingIds(prev => new Set(prev).add(id));
  }, [selectedProject, selectedChapter]);

  const handleClearDismissed = useCallback(async () => {
    if (!selectedProject) return;
    await clearDismissedSuggestions(selectedProject);
    setDismissedFindingIds(new Set());
  }, [selectedProject]);

  // ── 上下文建议接受 ──
  const handleAcceptContextSuggestion = useCallback(async (suggestion: ContextSuggestion) => {
    const ctx = projectContext;
    if (!ctx || !selectedProject) return;
    // 用 field_path 定位并修改 ProjectContext
    try {
      const updated = { ...ctx };
      const path = suggestion.field_path;
      // 简单路径解析
      if (path === "style_guide.prose_style" && updated.style_guide) {
        updated.style_guide = { ...updated.style_guide, prose_style: suggestion.suggested_value };
      } else if (path === "style_guide.sentence_preferences" && updated.style_guide) {
        updated.style_guide = { ...updated.style_guide, sentence_preferences: suggestion.suggested_value };
      } else if (path === "style_guide.dialogue_conventions" && updated.style_guide) {
        updated.style_guide = { ...updated.style_guide, dialogue_conventions: suggestion.suggested_value };
      } else if (path === "style_guide.narrative_distance" && updated.style_guide) {
        updated.style_guide = { ...updated.style_guide, narrative_distance: suggestion.suggested_value };
      } else if (path.startsWith("world_rules.")) {
        const field = path.replace("world_rules.", "");
        const wr = updated.world_rules ?? { magic_system: "", technology_level: "", social_structure: "", geography: "", custom_rules: [] };
        (wr as unknown as Record<string, unknown>)[field] = suggestion.suggested_value;
        updated.world_rules = wr;
      }
      await saveProjectContext(updated, ctx.context_version);
      await loadProjectContext();
      await setSuggestionState(suggestion.id, selectedProject, suggestion.chapter_id || "", "context_change", "accepted");
    } catch (e) {
      console.error("Accept suggestion failed:", e);
      alert(`应用建议失败: ${e}`);
    }
  }, [projectContext, selectedProject, saveProjectContext, loadProjectContext]);

  // ── 续写 ──
  const handleContinuation = useCallback(async () => {
    if (!selectedChapter || continuing) return;
    setContinuing(true);
    try {
      const result = await runContinuation(selectedChapter.id, editorContent);
      // 追加续写文本（用分隔注释标记）
      const continuation = "\n\n" + result.continuation_text;
      setContinuationPending(continuation);
      setContinuationCost(result.cost_usd);
      setEditorContent(prev => prev + continuation);
    } catch (e) {
      alert(`续写失败: ${e}`);
    } finally {
      setContinuing(false);
    }
  }, [selectedChapter, editorContent, continuing]);

  const handleAcceptContinuation = useCallback(() => {
    setContinuationPending(null);
    setContinuationCost(0);
  }, []);

  const handleRejectContinuation = useCallback(() => {
    if (continuationPending) {
      // 移除续写部分
      setEditorContent(prev => prev.replace(continuationPending, ""));
    }
    setContinuationPending(null);
    setContinuationCost(0);
  }, [continuationPending]);

  const handleRejectContextSuggestion = useCallback(async (suggestion: ContextSuggestion) => {
    if (!selectedProject) return;
    await setSuggestionState(suggestion.id, selectedProject, suggestion.chapter_id || "", "context_change", "dismissed");
  }, [selectedProject]);

  return (
    <div className="app" style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* 顶栏 */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          padding: "8px 16px",
          borderBottom: "1px solid #e0e0e0",
          background: "#fff",
        }}
      >
        <h1 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>
          📖 Narrative Mind
        </h1>
        <select
          value={selectedProject}
          onChange={(e) => {
            setSelectedProject(e.target.value);
            if (e.target.value) {
              loadProjectContext();
            }
            setViewMode("editor");
          }}
          style={{ fontSize: 13, padding: "4px 8px" }}
        >
          <option value="">选择项目...</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        {showNewProject ? (
          <span style={{ display: "flex", gap: 4, alignItems: "center" }}>
            <input
              autoFocus
              value={newProjectName}
              onChange={e => setNewProjectName(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter") handleNewProject();
                if (e.key === "Escape") { setShowNewProject(false); setNewProjectName(""); }
              }}
              placeholder="项目名称..."
              style={{ fontSize: 13, padding: "4px 8px", border: "1px solid #ccc", borderRadius: 4, width: 150 }}
            />
            <button onClick={handleNewProject} style={{ fontSize: 13, padding: "4px 8px", border: "none", borderRadius: 4, background: "#4285f4", color: "#fff", cursor: "pointer" }}>
              创建
            </button>
            <button onClick={() => { setShowNewProject(false); setNewProjectName(""); }}
              style={{ fontSize: 13, padding: "4px 8px", border: "1px solid #ccc", borderRadius: 4, background: "#fff", cursor: "pointer" }}>
              ✕
            </button>
          </span>
        ) : (
          <button onClick={() => setShowNewProject(true)} title="新建项目"
            style={{ fontSize: 18, padding: "0 6px", border: "1px solid #ccc", borderRadius: 4, background: "#fff", cursor: "pointer", lineHeight: "24px" }}>
            ＋
          </button>
        )}
        <span style={{ width: 1, background: "#e0e0e0", alignSelf: "stretch", margin: "4px 4px" }} />
        <button onClick={() => { if (selectedProject) { loadProjectContext(); setViewMode("settings"); } }}
          disabled={!selectedProject}
          title="项目设置"
          style={{ fontSize: 12, padding: "4px 8px", border: "1px solid #ccc", borderRadius: 4, background: "#fff", cursor: selectedProject ? "pointer" : "default", opacity: selectedProject ? 1 : 0.4 }}>
          ⚙️ 项目设置
        </button>
        <button onClick={() => { if (selectedProject) { setViewMode("import"); } }}
          disabled={!selectedProject}
          title="导入已有作品"
          style={{ fontSize: 12, padding: "4px 8px", border: "1px solid #ccc", borderRadius: 4, background: "#fff", cursor: selectedProject ? "pointer" : "default", opacity: selectedProject ? 1 : 0.4 }}>
          📥 导入
        </button>
        <button onClick={() => { if (selectedProject) { loadProjectContext(); setViewMode("golden"); } }}
          disabled={!selectedProject}
          title="一键黄金三章"
          style={{ fontSize: 12, padding: "4px 8px", border: "1px solid #f9ab00", borderRadius: 4, background: "#fff", color: "#e37400", cursor: selectedProject ? "pointer" : "default", opacity: selectedProject ? 1 : 0.4 }}>
          🚀 黄金三章
        </button>
      </header>

      {/* 主区域 */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* 章节列表侧边栏 */}
        <nav
          style={{
            width: 200,
            borderRight: "1px solid #e0e0e0",
            overflow: "auto",
            background: "#fafafa",
            padding: 8,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontWeight: 600, fontSize: 13 }}>📑 章节列表</span>
            <span style={{ flex: 1 }} />
            <button
              onClick={handleNewChapter}
              disabled={!selectedProject}
              title="新建章节"
              style={{
                fontSize: 14,
                padding: "0 5px",
                border: "1px solid #ccc",
                borderRadius: 3,
                background: "#fff",
                cursor: selectedProject ? "pointer" : "default",
                lineHeight: "20px",
                opacity: selectedProject ? 1 : 0.4,
              }}
            >
              ＋
            </button>
          </div>
          {chapters.map((ch) => (
            <div
              key={ch.id}
              onClick={() => handleSelectChapter(ch)}
              style={{
                padding: "6px 8px",
                cursor: "pointer",
                borderRadius: 4,
                background: selectedChapter?.id === ch.id ? "#e3f2fd" : "transparent",
                fontSize: 13,
                marginBottom: 2,
                display: "flex",
                alignItems: "center",
              }}
            >
              <span style={{ flex: 1 }}>{ch.title}</span>
              <span style={{ color: "#999", fontSize: 11, marginLeft: 4 }}>
                {ch.word_count} 字
              </span>
              <span
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteChapter(ch);
                }}
                title="删除章节"
                style={{
                  cursor: "pointer",
                  color: "#999",
                  marginLeft: 6,
                  fontSize: 12,
                }}
              >
                ✕
              </span>
            </div>
          ))}
          {selectedProject && <LibraryPanel projectId={selectedProject} />}
        </nav>

        {/* 主区域（编辑器 / 项目设置 / 导入） */}
        <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {viewMode === "settings" && selectedProject ? (
            <ProjectSettingsPanel
              projectId={selectedProject}
              projectContext={projectContext}
              onSave={async (ctx, expectedVersion) => {
                await saveProjectContext(ctx, expectedVersion);
                await loadProjectContext();
              }}
              onClose={() => setViewMode("editor")}
            />
          ) : viewMode === "import" && selectedProject ? (
            <ImportPanel
              projectId={selectedProject}
              onImport={async (ctx) => {
                await saveProjectContext(ctx);
                await loadProjectContext();
                setViewMode("editor");
              }}
              onClose={() => setViewMode("editor")}
            />
          ) : viewMode === "golden" && selectedProject ? (
            <GoldenThreeWizard
              projectId={selectedProject}
              projectContext={projectContext}
              onComplete={async () => {
                // 重新加载章节列表
                await storeLoadChapters();
              }}
              onClose={() => setViewMode("editor")}
            />
          ) : (
            <>
              {/* 编辑器工具栏 */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "4px 12px",
                  borderBottom: "1px solid #e0e0e0",
                  background: "#fff",
                }}
              >
                <span style={{ fontSize: 13, fontWeight: 600 }}>
                  {selectedChapter?.title ?? "未选择章节"}
                </span>
                <span style={{ flex: 1 }} />
                <button
                  onClick={handleQuickAnalyze}
                  disabled={!selectedChapter || storeAnalyzing}
                  style={{
                    padding: "4px 12px",
                    fontSize: 12,
                    background: storeAnalyzing ? "#ccc" : "#4285f4",
                    color: "#fff",
                    border: "none",
                    borderRadius: 4,
                    cursor: selectedChapter && !storeAnalyzing ? "pointer" : "default",
                  }}
                >
                  {storeAnalyzing ? "⏳ 分析中..." : "🔍 分析"}
                </button>
                <button
                  onClick={handleContinuation}
                  disabled={!selectedChapter || continuing}
                  style={{
                    padding: "4px 12px",
                    fontSize: 12,
                    border: "1px solid #4285f4",
                    borderRadius: 4,
                    background: continuing ? "#e8f0fe" : "#fff",
                    color: "#4285f4",
                    cursor: selectedChapter && !continuing ? "pointer" : "default",
                  }}
                >
                  {continuing ? "⏳ 续写中..." : "✨ 续写"}
                </button>
                <button
                  onClick={handleSave}
                  disabled={!selectedChapter}
                  style={{
                    padding: "4px 12px",
                    fontSize: 12,
                    border: "1px solid #ccc",
                    borderRadius: 4,
                    background: "#fff",
                    cursor: selectedChapter ? "pointer" : "default",
                  }}
                >
                  💾 保存
                </button>
              </div>
              {/* 续写确认条 */}
              {continuationPending && (
                <div style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "6px 12px", background: "#fef7e0", borderBottom: "1px solid #f9ab00",
                  fontSize: 12,
                }}>
                  <span style={{ color: "#e37400", flex: 1 }}>
                    AI 续写了内容（约 {continuationPending.length} 字符）💰 ${continuationCost.toFixed(4)}
                  </span>
                  <button onClick={handleAcceptContinuation}
                    style={{ padding: "3px 10px", fontSize: 12, border: "none", borderRadius: 3, background: "#34a853", color: "#fff", cursor: "pointer" }}>
                    ✅ 接受
                  </button>
                  <button onClick={handleRejectContinuation}
                    style={{ padding: "3px 10px", fontSize: 12, border: "1px solid #e74c3c", borderRadius: 3, background: "#fff", color: "#e74c3c", cursor: "pointer" }}>
                    ❌ 拒绝
                  </button>
                </div>
              )}

              {selectedProject && !selectedChapter && !projectContext ? (
                /* 引导提示：项目无章节且无创作上下文 */
                <div style={{
                  flex: 1, display: "flex", flexDirection: "column",
                  alignItems: "center", justifyContent: "center", gap: 16,
                  color: "#888", background: "#fafafa",
                }}>
                  <div style={{ fontSize: 48 }}>📝</div>
                  <div style={{ fontSize: 16, fontWeight: 600 }}>欢迎来到创作工坊</div>
                  <div style={{ fontSize: 13, textAlign: "center", maxWidth: 360 }}>
                    请先完成项目设置或导入已有文本，然后开始创作你的故事。
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={() => { loadProjectContext(); setViewMode("settings"); }}
                      style={{ padding: "8px 20px", fontSize: 13, border: "none", borderRadius: 4, background: "#4285f4", color: "#fff", cursor: "pointer" }}>
                      ⚙️ 项目设置
                    </button>
                    <button onClick={() => setViewMode("import")}
                      style={{ padding: "8px 20px", fontSize: 13, border: "1px solid #4285f4", borderRadius: 4, background: "#fff", color: "#4285f4", cursor: "pointer" }}>
                      📥 导入已有作品
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div style={{ flex: 1, overflow: "hidden" }}>
                    <Editor
                      content={editorContent}
                      onChange={setEditorContent}
                      annotations={annotations}
                      proposals={proposals}
                    />
                  </div>

                  {/* 状态栏 */}
                  <StatusBar
                    agents={agentStates}
                    topology={storeAnalysisResult?.topology}
                    complexity={storeAnalysisResult?.complexity}
                    totalCost={totalCost}
                  />
                </>
              )}
            </>
          )}
        </main>

        {/* 分析面板侧边栏 */}
        <aside
          style={{
            width: 320,
            borderLeft: "1px solid #e0e0e0",
            overflow: "auto",
            background: "#fafafa",
          }}
        >
          {showContextSuggestions && contextSuggestions.length > 0 ? (
            <ContextSuggestionsPanel
              suggestions={contextSuggestions}
              projectContext={projectContext}
              onAccept={handleAcceptContextSuggestion}
              onReject={handleRejectContextSuggestion}
              onClose={() => setShowContextSuggestions(false)}
            />
          ) : (
            <StickyBoard
              agentStates={agentStates}
              dismissedFindingIds={dismissedFindingIds}
              contextSuggestions={contextSuggestions}
              onDismissFinding={handleDismissFinding}
              onSnoozeFinding={handleSnoozeFinding}
              onClearDismissed={handleClearDismissed}
              onShowContextSuggestions={() => setShowContextSuggestions(true)}
            />
          )}
        </aside>
      </div>
    </div>
  );
}

export default App;
