/**
 * Narrative Mind v4.0 — 主应用组件
 *
 * Phase E: Monaco Editor + Agent 标注 + 分析面板 + 状态栏
 * Phase K: 分析结果迁移到 Zustand store，AnalysisPanel 改为结果浏览器
 */

import { useState, useCallback, useEffect } from "react";
import { Editor, StatusBar, StickyBoard, LibraryPanel } from "./components";
import { listProjects, listChapters, createProject, createChapter, updateChapter, deleteChapter, runAnalysis, onAgentProgress, onProposalReady, onAnalysisComplete } from "./api";
import type { ProjectMeta, ChapterData, AnalysisComplete } from "./api";
import type { ProposalReady } from "./api/events";
import type { AgentState, AgentAnnotation } from "./types";
import { useAppStore } from "./store";
import "./App.css";

function App() {
  // ── Zustand store ──
  const storeAnalysisResult = useAppStore((s) => s.analysisResult);
  const storeAnalyzing = useAppStore((s) => s.analyzing);
  const setAnalysisResult = useAppStore((s) => s.setAnalysisResult);
  const setAnalyzing = useAppStore((s) => s.setAnalyzing);

  // ── 本地状态 ──
  const [projects, setProjects] = useState<ProjectMeta[]>([]);
  const [chapters, setChapters] = useState<ChapterData[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [selectedChapter, setSelectedChapter] = useState<ChapterData | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [annotations, setAnnotations] = useState<AgentAnnotation[]>([]);
  const [proposals, setProposals] = useState<ProposalReady[]>([]);
  const [agentStates, setAgentStates] = useState<AgentState[]>([]);
  const [totalCost, setTotalCost] = useState(0);

  // ── 加载项目列表 ──
  useEffect(() => {
    listProjects().then(setProjects).catch(console.error);
  }, []);

  // ── 加载章节列表 ──
  useEffect(() => {
    if (selectedProject) {
      listChapters(selectedProject).then(setChapters).catch(console.error);
    }
  }, [selectedProject]);

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
  }, []);

  // ── 新建项目 ──
  const handleNewProject = useCallback(async () => {
    const name = prompt("项目名称：");
    if (!name?.trim()) return;
    try {
      const p = await createProject(name.trim());
      setProjects((prev) => [...prev, p]);
      setSelectedProject(p.id);
    } catch (e) {
      alert(`创建项目失败: ${e}`);
    }
  }, []);

  // ── 新建章节 ──
  const handleNewChapter = useCallback(async () => {
    if (!selectedProject) return;
    const title = prompt("章节标题：");
    if (!title?.trim()) return;
    try {
      const ch = await createChapter(selectedProject, title.trim(), "");
      setChapters((prev) => [...prev, ch]);
      setSelectedChapter(ch);
      setEditorContent(ch.text);
    } catch (e) {
      alert(`创建章节失败: ${e}`);
    }
  }, [selectedProject]);

  // ── 删除章节 ──
  const handleDeleteChapter = useCallback(
    async (ch: ChapterData) => {
      if (!confirm(`删除章节 "${ch.title}"？`)) return;
      try {
        await deleteChapter(ch.id);
        setChapters((prev) => prev.filter((c) => c.id !== ch.id));
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
    [selectedChapter]
  );

  // ── 保存 ──
  const handleSave = useCallback(async () => {
    if (!selectedChapter) return;
    const updated = { ...selectedChapter, text: editorContent };
    try {
      const saved = await updateChapter(updated);
      setSelectedChapter(saved);
      setChapters((prev) => prev.map((c) => c.id === saved.id ? saved : c));
    } catch (e) {
      alert(`保存失败: ${e}`);
    }
  }, [selectedChapter, editorContent]);

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
    try {
      const result = await runAnalysis(selectedChapter.id, "scene_analysis");
      setAnalysisResult(result);
      applyAnnotations(result);
    } catch (e) {
      alert(`分析失败: ${e}`);
      setAnalyzing(false);
    }
  }, [selectedChapter, storeAnalyzing, setAnalyzing, setAnalysisResult, applyAnnotations]);

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
          onChange={(e) => setSelectedProject(e.target.value)}
          style={{ fontSize: 13, padding: "4px 8px" }}
        >
          <option value="">选择项目...</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <button
          onClick={handleNewProject}
          title="新建项目"
          style={{
            fontSize: 18,
            padding: "0 6px",
            border: "1px solid #ccc",
            borderRadius: 4,
            background: "#fff",
            cursor: "pointer",
            lineHeight: "24px",
          }}
        >
          ＋
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

        {/* 编辑器 */}
        <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
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
          <StickyBoard agentStates={agentStates} />
        </aside>
      </div>
    </div>
  );
}

export default App;
