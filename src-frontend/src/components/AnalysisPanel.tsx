/**
 * 分析结果浏览器 — Narrative Mind v4.0
 *
 * 重构：从"9 按钮触发分析 + 原始 JSON"改为"Tab 切换 + 结构化卡片"。
 * 分析结果缓存在 Zustand store 中，切换标签不触发重新分析。
 */

import { useState, useMemo } from "react";
import { useAppStore } from "../store";
import type { AgentFinding, AgentId, AgentState } from "../types";
import type { AnalysisOutput } from "../api";
import { FindingsCard } from "./FindingsCard";
import { PADView } from "./PADView";
import { ProgressBar } from "./ProgressBar";

// =========================================================================
// Tab 配置
// =========================================================================

interface TabDef {
  key: string;
  label: string;
  icon: string;
  /** 过滤 findings 的 agent_id（null = 全部） */
  filterAgent: AgentId | null;
}

const TABS: TabDef[] = [
  { key: "overview", label: "总览", icon: "📋", filterAgent: null },
  { key: "pad", label: "PAD", icon: "🎭", filterAgent: "Character" },
  { key: "entity", label: "实体", icon: "👤", filterAgent: "Character" },
  { key: "rule", label: "规则", icon: "📋", filterAgent: "World" },
  { key: "narrative", label: "伏笔", icon: "🔍", filterAgent: "Narrative" },
  { key: "prose", label: "文风", icon: "✒️", filterAgent: "Prose" },
  { key: "theme", label: "主题", icon: "🎯", filterAgent: "Theme" },
  { key: "economy", label: "经济", icon: "📊", filterAgent: "Economy" },
  { key: "scene", label: "场景", icon: "🎬", filterAgent: "EditorInChief" },
];

// =========================================================================
// Agent 中文名映射
// =========================================================================

const AGENT_NAMES: Record<string, string> = {
  Character: "角色 Agent",
  World: "世界 Agent",
  Narrative: "叙事 Agent",
  Prose: "文辞 Agent",
  Theme: "主题 Agent",
  Economy: "经济 Agent",
  ReaderExpectation: "预期 Agent",
  Conception: "构思 Agent",
  EditorInChief: "总编 Agent",
};

// =========================================================================
// 从 agent_outputs 中提取指定 agent 的原始 JSON
// =========================================================================

function findAgentOutput(result: AnalysisOutput, agentId: string): string | null {
  const ao = result.agent_outputs.find((a) => a.agent_id === agentId);
  return ao?.output ?? null;
}

/** 尝试从 agent output JSON 中解析 PAD 数据 */
function parsePAD(output: string | null): {
  pleasure: number;
  arousal: number;
  dominance: number;
  rationale?: string;
} | null {
  if (!output) return null;
  try {
    const obj = JSON.parse(output);
    if ("pleasure" in obj || "arousal" in obj || "dominance" in obj) {
      return {
        pleasure: typeof obj.pleasure === "number" ? obj.pleasure : 0,
        arousal: typeof obj.arousal === "number" ? obj.arousal : 0,
        dominance: typeof obj.dominance === "number" ? obj.dominance : 0,
        rationale: typeof obj.rationale === "string" ? obj.rationale : undefined,
      };
    }
  } catch {
    // 不是 JSON，忽略
  }
  return null;
}

// =========================================================================
// AnalysisPanel
// =========================================================================

interface AnalysisPanelProps {
  /** Agent 实时状态（来自 App.tsx 事件监听），用于进度条 */
  agentStates?: AgentState[];
}

export function AnalysisPanel({ agentStates = [] }: AnalysisPanelProps) {
  const analysisResult = useAppStore((s) => s.analysisResult);
  const analyzing = useAppStore((s) => s.analyzing);
  // agentStates 暂时从 App.tsx 通过事件管理，后续可迁移
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [showRawJson, setShowRawJson] = useState(false);

  // 根据标签过滤 findings
  const filteredFindings = useMemo(() => {
    if (!analysisResult?.findings) return [];
    const tab = TABS.find((t) => t.key === activeTab);
    if (!tab || tab.filterAgent === null) {
      return analysisResult.findings;
    }
    return analysisResult.findings.filter((f) => f.agent_id === tab.filterAgent);
  }, [analysisResult, activeTab]);

  // 分组 findings（仅总览标签）
  const groupedFindings = useMemo(() => {
    if (activeTab !== "overview" || !analysisResult?.findings) return null;
    const groups: Record<string, AgentFinding[]> = {};
    for (const f of analysisResult.findings) {
      if (!groups[f.agent_id]) groups[f.agent_id] = [];
      groups[f.agent_id].push(f);
    }
    return groups;
  }, [analysisResult, activeTab]);

  // PAD 数据（Character agent output）
  const padData = useMemo(() => {
    if (!analysisResult) return null;
    return parsePAD(findAgentOutput(analysisResult, "Character"));
  }, [analysisResult]);

  return (
    <div
      className="analysis-panel"
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        fontSize: 13,
      }}
    >
      {/* 标题行 + 进度条 */}
      <div style={{ fontWeight: 600, padding: "12px 12px 0" }}>🤖 Agent 分析</div>

      {/* 分析中：显示进度条；分析完：显示摘要 */}
      {analyzing && (
        <ProgressBar agents={agentStates} active={true} />
      )}
      {!analyzing && analysisResult && (
        <ProgressBar
          agents={agentStates}
          active={false}
          findingsCount={analysisResult.findings.length}
        />
      )}

      {/* Tab 导航（仅在有结果时显示） */}
      {analysisResult && !analyzing && (
        <>
          {/* TabBar */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 2,
              padding: "8px 8px 0",
              borderBottom: "1px solid #e0e0e0",
            }}
          >
            {TABS.map((tab) => {
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  style={{
                    padding: "4px 8px",
                    fontSize: 12,
                    border: "none",
                    borderBottom: isActive ? "2px solid #4285f4" : "2px solid transparent",
                    background: isActive ? "#e8f0fe" : "transparent",
                    color: isActive ? "#4285f4" : "#666",
                    fontWeight: isActive ? 600 : 400,
                    cursor: "pointer",
                    borderRadius: "4px 4px 0 0",
                    whiteSpace: "nowrap",
                  }}
                >
                  {tab.icon} {tab.label}
                </button>
              );
            })}
          </div>

          {/* 内容区 */}
          <div
            style={{
              flex: 1,
              overflow: "auto",
              padding: "8px 10px",
            }}
          >
            {/* PAD 标签专用视图 */}
            {activeTab === "pad" && padData && (
              <PADView
                pleasure={padData.pleasure}
                arousal={padData.arousal}
                dominance={padData.dominance}
                rationale={padData.rationale}
              />
            )}

            {/* 总览标签：按 Agent 分组 */}
            {activeTab === "overview" && groupedFindings && (
              <>
                {Object.entries(groupedFindings).map(([agentId, findings]) => (
                  <div key={agentId} style={{ marginBottom: 12 }}>
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 600,
                        color: "#555",
                        marginBottom: 4,
                        padding: "2px 4px",
                        background: "#f0f0f0",
                        borderRadius: 3,
                      }}
                    >
                      {AGENT_NAMES[agentId] ?? agentId} ({findings.length})
                    </div>
                    {findings.map((f, i) => (
                      <FindingsCard
                        key={`${f.agent_id}-${f.title}-${i}`}
                        finding={f}
                        agentName={AGENT_NAMES[f.agent_id] ?? f.agent_id}
                      />
                    ))}
                  </div>
                ))}
                {Object.keys(groupedFindings).length === 0 && (
                  <EmptyState />
                )}
              </>
            )}

            {/* 非总览标签：简单列表 */}
            {activeTab !== "overview" && (
              <>
                {activeTab !== "pad" && filteredFindings.map((f, i) => (
                  <FindingsCard
                    key={`${f.agent_id}-${f.title}-${i}`}
                    finding={f}
                    agentName={AGENT_NAMES[f.agent_id] ?? f.agent_id}
                  />
                ))}
                {activeTab === "pad" && filteredFindings.map((f, i) => (
                  <FindingsCard
                    key={`${f.agent_id}-${f.title}-${i}`}
                    finding={f}
                    agentName={AGENT_NAMES[f.agent_id] ?? f.agent_id}
                  />
                ))}
                {filteredFindings.length === 0 && (!padData || activeTab !== "pad") && (
                  <EmptyState />
                )}
              </>
            )}

            {/* 原始 JSON 调试开关 */}
            <div style={{ marginTop: 16, borderTop: "1px solid #eee", paddingTop: 8 }}>
              <button
                onClick={() => setShowRawJson(!showRawJson)}
                style={{
                  fontSize: 11,
                  color: "#999",
                  border: "none",
                  background: "none",
                  cursor: "pointer",
                  padding: 0,
                }}
              >
                {showRawJson ? "▲ 收起" : "▶ 查看原始 JSON（调试）"}
              </button>
              {showRawJson && (
                <pre
                  style={{
                    marginTop: 4,
                    fontSize: 10,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-all",
                    maxHeight: 200,
                    overflow: "auto",
                    background: "#f5f5f5",
                    padding: 8,
                    borderRadius: 4,
                    color: "#666",
                  }}
                >
                  {analysisResult.agent_outputs
                    .map((ao) => `=== ${ao.agent_name} (${ao.agent_id}) ===\n${ao.output}`)
                    .join("\n\n")}
                </pre>
              )}
            </div>
          </div>

          {/* 底部元信息 */}
          <div
            style={{
              padding: "6px 12px",
              borderTop: "1px solid #e0e0e0",
              fontSize: 11,
              color: "#999",
              background: "#fafafa",
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            <span>🔀 {analysisResult.topology}</span>
            <span>📊 {analysisResult.complexity}</span>
            {analysisResult.total_cost_usd > 0 && (
              <span style={{ marginLeft: "auto" }}>💰 ${analysisResult.total_cost_usd.toFixed(4)}</span>
            )}
          </div>
        </>
      )}

      {/* 无结果时的提示 */}
      {!analysisResult && !analyzing && (
        <div style={{ padding: 24, color: "#999", fontSize: 13, textAlign: "center" }}>
          点击工具栏 <span style={{ color: "#4285f4", fontWeight: 600 }}>🔍 分析</span> 开始
        </div>
      )}
    </div>
  );
}

// =========================================================================
// 空状态
// =========================================================================

function EmptyState() {
  return (
    <div style={{ padding: 24, color: "#bbb", fontSize: 13, textAlign: "center" }}>
      此分类下暂无发现
    </div>
  );
}
