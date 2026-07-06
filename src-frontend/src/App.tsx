/**
 * Narrative Mind v4.0 — 主应用组件
 *
 * Phase E: Monaco Editor + Agent 标注 + 分析面板 + 状态栏
 */

import { useState, useCallback, useEffect } from "react";
import { Editor, StatusBar, AnalysisPanel } from "./components";
import { listProjects, listChapters, onAgentProgress, onAnalysisComplete } from "./api";
import type { ProjectMeta, ChapterData, AnalysisComplete } from "./api";
import type { AgentState, AgentAnnotation } from "./types";
import type { AnalysisOutput } from "./api";
import "./App.css";

function App() {
  // ── 状态 ──
  const [projects, setProjects] = useState<ProjectMeta[]>([]);
  const [chapters, setChapters] = useState<ChapterData[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [selectedChapter, setSelectedChapter] = useState<ChapterData | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [annotations, setAnnotations] = useState<AgentAnnotation[]>([]);
  const [agentStates, setAgentStates] = useState<AgentState[]>([]);
  const [topology, setTopology] = useState<string>();
  const [complexity, setComplexity] = useState<string>();
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

    const unlisten2 = onAnalysisComplete((evt: AnalysisComplete) => {
      // 标记所有 Agent 为完成
      setAgentStates((prev) =>
        prev.map((a) => (a.status === "running" ? { ...a, status: "done", progress: 100 } : a))
      );
      setTotalCost((prev) => prev + evt.total_cost);
    });

    return () => {
      unlisten1.then((fn) => fn());
      unlisten2.then((fn) => fn());
    };
  }, []);

  // ── 章节选择 ──
  const handleSelectChapter = useCallback((ch: ChapterData) => {
    setSelectedChapter(ch);
    setEditorContent(ch.text);
    setAnnotations([]);
    setAgentStates([]);
  }, []);

  // ── 分析结果处理 ──
  const handleAnalysisResult = useCallback(
    (result: AnalysisOutput) => {
      setTopology(result.topology);
      setComplexity(result.complexity);

      // 将 Agent 输出转换为标注（简化版：整段标注）
      const newAnnotations: AgentAnnotation[] = result.agent_outputs.map(
        (ao, idx) => ({
          id: `${result.request_id}-${ao.agent_id}`,
          agent_id: ao.agent_id,
          agent_name: ao.agent_name,
          message: ao.output.substring(0, 200),
          severity: "info" as const,
          location: {
            start_line: 1 + idx,
            start_column: 1,
            end_line: 1 + idx,
            end_column: 10,
          },
        })
      );
      setAnnotations(newAnnotations);
    },
    []
  );

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
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
            📑 章节列表
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
              }}
            >
              {ch.title}
              <span style={{ color: "#999", fontSize: 11, marginLeft: 4 }}>
                {ch.word_count} 字
              </span>
            </div>
          ))}
        </nav>

        {/* 编辑器 */}
        <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ flex: 1, overflow: "hidden" }}>
            <Editor
              content={editorContent}
              onChange={setEditorContent}
              annotations={annotations}
            />
          </div>

          {/* 状态栏 */}
          <StatusBar
            agents={agentStates}
            topology={topology}
            complexity={complexity}
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
          {selectedChapter ? (
            <AnalysisPanel
              chapterId={selectedChapter.id}
              onResult={handleAnalysisResult}
              onError={(err) => console.error("Analysis error:", err)}
            />
          ) : (
            <div style={{ padding: 16, color: "#999", fontSize: 13, textAlign: "center" }}>
              选择章节以开始分析
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

export default App;
