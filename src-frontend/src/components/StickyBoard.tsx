/**
 * StickyBoard — Phase L3: 便签风格上下文提示板
 *
 * 三状态切换: 暖场便签 | 分析进度 | 便签列表
 * 替代 App.tsx 右侧 aside 中的 <AnalysisPanel />。
 */

import { useState, useMemo, useCallback, type FC } from "react";
import { useAppStore } from "../store";
import { ProgressBar } from "./ProgressBar";
import { FindingsCard } from "./FindingsCard";
import type { AgentFinding, AgentState, ContextSuggestion } from "../types";

// =========================================================================
// StickyNote 类型
// =========================================================================

interface StickyNote {
  id: string;
  color: string;
  icon: string;
  title: string;
  lines: string[];
  pinned?: boolean;
  dismissible?: boolean;
}

// =========================================================================
// PAD → 自然语言
// =========================================================================

function padToNatural(p: number, a: number, d: number): string {
  const pleasure = p > 0.3 ? "愉悦" : p < -0.3 ? "低落" : "平静";
  const arousal = a > 0.3 ? "激动" : a < -0.3 ? "冷淡" : "中性";
  const dominance = d > 0.3 ? "掌控" : d < -0.3 ? "顺从" : "平和";

  // 找最突出的维度
  const absP = Math.abs(p);
  const absA = Math.abs(a);
  const absD = Math.abs(d);
  if (absP >= absA && absP >= absD) return pleasure;
  if (absA >= absP && absA >= absD) return arousal + "状态";
  return dominance;
}

function parsePADFromOutput(output: string): { pleasure: number; arousal: number; dominance: number } | null {
  try {
    const obj = JSON.parse(output);
    if (typeof obj.pleasure === "number" && typeof obj.arousal === "number" && typeof obj.dominance === "number") {
      return { pleasure: obj.pleasure, arousal: obj.arousal, dominance: obj.dominance };
    }
  } catch { /* not JSON */ }
  return null;
}

// =========================================================================
// 颜色排序权重
// =========================================================================

const COLOR_WEIGHT: Record<string, number> = {
  "#fce8e6": 0,  // 红色 — 问题 (最前)
  "#fef7e0": 1,  // 黄色 — 伏笔
  "#e8f5e9": 2,  // 绿色 — 人物
  "#e8f0fe": 3,  // 蓝色 — 位置
  "#f5f5f5": 4,  // 灰色 — 总结/详情 (最后)
};

// =========================================================================
// 暖场便签
// =========================================================================

const WARMUP_NOTES: StickyNote[] = [
  { id: "warmup-1", color: "#f5f5f5", icon: "📝", title: "写作检查清单", lines: [
    "✓ 场景是否有明确的目标？",
    "✓ 角色情绪是否连贯？",
    "✓ 对话风格是否一致？",
    "✓ 地点/空间描述是否清晰？",
    "✓ 伏笔是否有回收计划？",
    "✓ 时间线是否有矛盾？",
  ]},
  { id: "warmup-2", color: "#e8f0fe", icon: "💡", title: "提示", lines: [
    "点击工具栏 🔍 分析 按钮，",
    "AI Agent 将自动检测：",
    "· 角色性格与情绪 (PAD)",
    "· 空间/规则一致性",
    "· 伏笔生命周期",
    "· 句长/语域/修辞",
    "· 主题强度追踪",
    "",
    "分析完成后此处显示便签卡片。",
  ]},
];

// =========================================================================
// StickyBoard 组件
// =========================================================================

interface StickyBoardProps {
  agentStates?: AgentState[];
  dismissedFindingIds?: Set<string>;
  contextSuggestions?: ContextSuggestion[];
  onDismissFinding?: (id: string) => void;
  onSnoozeFinding?: (id: string) => void;
  onClearDismissed?: () => void;
  onShowContextSuggestions?: () => void;
}

export const StickyBoard: FC<StickyBoardProps> = ({
  agentStates = [],
  dismissedFindingIds = new Set(),
  contextSuggestions,
  onDismissFinding,
  onSnoozeFinding,
  onClearDismissed,
  onShowContextSuggestions,
}) => {
  // ── Zustand store ──
  const analysisResult = useAppStore((s) => s.analysisResult);
  const analyzing = useAppStore((s) => s.analyzing);
  const characters = useAppStore((s) => s.characters);
  const locations = useAppStore((s) => s.locations);
  const foreshadows = useAppStore((s) => s.foreshadows);

  // ── 本地状态 ──
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [showDetail, setShowDetail] = useState(false);

  // ── 从 analysisResult 构建便签 ──
  const notes = useMemo<StickyNote[]>(() => {
    if (!analysisResult) return [];

    const result: StickyNote[] = [];
    const findings = analysisResult.findings ?? [];

    // 1. 章节总结 (#f5f5f5) — EditorInChief findings 第一条
    const eicFindings = findings.filter((f) => f.agent_id === "EditorInChief");
    if (eicFindings.length > 0) {
      result.push({
        id: "summary",
        color: "#f5f5f5",
        icon: "📖",
        title: "章节总结",
        lines: [eicFindings[0].description.length > 120
          ? eicFindings[0].description.slice(0, 120) + "…"
          : eicFindings[0].description],
        dismissible: true,
      });
    }

    // 2. 当前位置 (#e8f0fe) — extracted_locations + locations 库
    const extractedLocs = analysisResult.extracted_locations ?? [];
    if (extractedLocs.length > 0) {
      const locLines = extractedLocs.map((l) => `${l.name}${l.location_type ? ` (${l.location_type})` : ""}${l.description ? `: ${l.description.slice(0, 60)}` : ""}`);
      result.push({
        id: "location",
        color: "#e8f0fe",
        icon: "📍",
        title: `当前位置${extractedLocs.length > 1 ? ` (${extractedLocs.length}处)` : ""}`,
        lines: locLines.length > 0 ? locLines : ["(未识别到具体地点)"],
        dismissible: true,
      });
    }

    // 3. 场景人物 (#e8f5e9) — extracted_characters + PAD
    const extractedChars = analysisResult.extracted_characters ?? [];
    const charLines: string[] = [];
    for (const c of extractedChars) {
      // 尝试从 Character agent output 解析 PAD
      let padLabel = "";
      const charOutput = analysisResult.agent_outputs.find((ao) => ao.agent_id === "Character");
      if (charOutput) {
        const pad = parsePADFromOutput(charOutput.output);
        if (pad) {
          padLabel = ` · ${padToNatural(pad.pleasure, pad.arousal, pad.dominance)}`;
        }
      }
      charLines.push(`${c.name || "(未命名)"}${c.role ? ` · ${c.role}` : ""}${padLabel}`);
    }
    if (charLines.length > 0) {
      result.push({
        id: "characters",
        color: "#e8f5e9",
        icon: "👤",
        title: `场景人物 (${extractedChars.length})`,
        lines: charLines,
        dismissible: true,
      });
    }

    // 4. 待回收伏笔 (#fef7e0) — foreshadows 过滤 status!=Resolved
    const pendingForeshadows = foreshadows.filter((f) => f.status !== "Resolved");
    if (pendingForeshadows.length > 0) {
      result.push({
        id: "foreshadow",
        color: "#fef7e0",
        icon: "🔮",
        title: `待回收伏笔 (${pendingForeshadows.length})`,
        lines: pendingForeshadows.map((f) => `${f.title} (⚠️${f.status})`),
        dismissible: true,
      });
    }

    // 5. 问题 (#fce8e6) — findings 过滤 severity=Critical/Warn
    const problems = findings.filter((f) => f.severity === "Critical" || f.severity === "Warn");
    if (problems.length > 0) {
      result.push({
        id: "problems",
        color: "#fce8e6",
        icon: "⚠️",
        title: `问题 (${problems.length})`,
        lines: problems.map((f) => `[${f.severity}] ${f.title}`),
        dismissible: true,
      });
    }

    // 6. 分析详情 (#f5f5f5) — 折叠折叠面板
    result.push({
      id: "detail-toggle",
      color: "#f5f5f5",
      icon: "📊",
      title: `分析详情 (${findings.length} 条发现)`,
      lines: ["点击展开查看完整分析结果"],
      pinned: true,
    });

    return result;
  }, [analysisResult, characters, locations, foreshadows]);

  // ── 过滤 + 排序 ──
  const visibleNotes = useMemo(() => {
    const filtered = notes.filter((n) => !dismissedIds.has(n.id));
    // pinned 的保持原位（pinned 不是排序，而是"下次分析不刷新"），按颜色排序
    return filtered.sort((a, b) => {
      const wa = COLOR_WEIGHT[a.color] ?? 5;
      const wb = COLOR_WEIGHT[b.color] ?? 5;
      return wa - wb;
    });
  }, [notes, dismissedIds]);

  // ── 钉住切换 ──
  const togglePin = useCallback((id: string) => {
    setPinnedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  // ── 撕掉 ──
  const dismiss = useCallback((id: string) => {
    setDismissedIds((prev) => new Set(prev).add(id));
  }, []);

  // ── 展开/折叠 ──
  const toggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  // ── 渲染单张便签 ──
  const renderNote = (note: StickyNote) => {
    const isExpanded = expandedIds.has(note.id);
    const isPinned = pinnedIds.has(note.id);
    const isDetail = note.id === "detail-toggle";
    const MAX_LINES = 3;
    const needsCollapse = note.lines.length > MAX_LINES;
    const displayLines = isExpanded || !needsCollapse ? note.lines : note.lines.slice(0, MAX_LINES);

    // "分析详情" 便签特殊处理
    if (isDetail && showDetail) {
      return renderDetailCard();
    }

    return (
      <div
        key={note.id}
        style={{
          background: note.color,
          borderRadius: 6,
          padding: "8px 10px",
          marginBottom: 6,
          border: "1px solid rgba(0,0,0,0.06)",
          position: "relative",
          fontSize: 12,
          lineHeight: 1.5,
        }}
      >
        {/* 标题行 */}
        <div
          onClick={() => isDetail ? setShowDetail(!showDetail) : toggleExpand(note.id)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            cursor: "pointer",
            marginBottom: 4,
          }}
        >
          <span>{note.icon}</span>
          <span style={{ fontWeight: 600, fontSize: 12, flex: 1 }}>{note.title}</span>
          {/* 钉住按钮 */}
          {note.pinned !== undefined && (
            <button
              onClick={(e) => { e.stopPropagation(); togglePin(note.id); }}
              title={isPinned ? "已钉住，点击取消" : "钉住此便签"}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                fontSize: 12,
                opacity: isPinned ? 1 : 0.3,
                padding: 0,
                lineHeight: 1,
              }}
            >
              📌
            </button>
          )}
          {/* 撕掉按钮 */}
          {note.dismissible && (
            <button
              onClick={(e) => { e.stopPropagation(); dismiss(note.id); }}
              title="撕掉此便签"
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                fontSize: 12,
                opacity: 0.3,
                padding: 0,
                lineHeight: 1,
              }}
            >
              ✕
            </button>
          )}
        </div>

        {/* 内容行 */}
        {displayLines.map((line, i) => (
          <div key={i} style={{ paddingLeft: 18, color: "#444", fontSize: 11 }}>
            {line || " "}
          </div>
        ))}

        {/* 折叠提示 */}
        {needsCollapse && !isExpanded && (
          <div
            onClick={() => toggleExpand(note.id)}
            style={{ paddingLeft: 18, color: "#999", fontSize: 11, cursor: "pointer", marginTop: 2 }}
          >
            … 还有 {note.lines.length - MAX_LINES} 行，点击展开
          </div>
        )}
        {needsCollapse && isExpanded && (
          <div
            onClick={() => toggleExpand(note.id)}
            style={{ paddingLeft: 18, color: "#999", fontSize: 11, cursor: "pointer", marginTop: 2 }}
          >
            ▲ 收起
          </div>
        )}
      </div>
    );
  };

  // ── 分析详情卡片（替换折叠面板） ──
  const renderDetailCard = () => {
    if (!analysisResult) return null;
    const findings = analysisResult.findings ?? [];
    const groups: Record<string, AgentFinding[]> = {};
    for (const f of findings) {
      if (!groups[f.agent_id]) groups[f.agent_id] = [];
      groups[f.agent_id].push(f);
    }
    const AGENT_NAMES: Record<string, string> = {
      Character: "角色 Agent", World: "世界 Agent", Narrative: "叙事 Agent",
      Prose: "文辞 Agent", Theme: "主题 Agent", Economy: "经济 Agent",
      ReaderExpectation: "预期 Agent", Conception: "构思 Agent", EditorInChief: "总编 Agent",
      EntityExtract: "实体提取 Agent",
    };

    return (
      <div key="detail-expanded" style={{ marginBottom: 6 }}>
        <div
          onClick={() => setShowDetail(false)}
          style={{
            background: "#f5f5f5", borderRadius: 6, padding: "8px 10px", marginBottom: 4,
            border: "1px solid rgba(0,0,0,0.06)", cursor: "pointer",
            display: "flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600,
          }}
        >
          📊 分析详情 ({findings.length} 条发现) ▲ 收起
        </div>
        <div style={{ maxHeight: 360, overflow: "auto", paddingRight: 2 }}>
          {Object.entries(groups).map(([agentId, agentFindings]) => (
            <div key={agentId} style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#555", marginBottom: 3, padding: "2px 4px", background: "#f0f0f0", borderRadius: 3 }}>
                {AGENT_NAMES[agentId] ?? agentId} ({agentFindings.length})
              </div>
              {agentFindings.map((f, i) => (
                {dismissedFindingIds.has(f.id ?? "") ? null : (
                  <FindingsCard
                    key={`${f.agent_id}-${f.title}-${i}`}
                    finding={f}
                    agentName={AGENT_NAMES[f.agent_id] ?? f.agent_id}
                    onDismiss={onDismissFinding}
                    onSnooze={onSnoozeFinding}
                    isDismissed={dismissedFindingIds.has(f.id ?? "")}
                  />
                )}
              ))}
            </div>
          ))}
        </div>
        {/* 上下文建议链接 + 隐藏计数 */}
        {(contextSuggestions && contextSuggestions.length > 0 || dismissedFindingIds.size > 0) && (
          <div style={{
            padding: "6px 8px", display: "flex", gap: 8, alignItems: "center",
            borderBottom: "1px solid #f0f0f0", background: "#fafafa", fontSize: 11,
          }}>
            {contextSuggestions && contextSuggestions.length > 0 && (
              <span
                onClick={onShowContextSuggestions}
                style={{ cursor: "pointer", color: "#4285f4", fontWeight: 600, flex: 1 }}
              >
                📝 {contextSuggestions.length} 条上下文修订建议
              </span>
            )}
            {dismissedFindingIds.size > 0 && (
              <>
                <span style={{ color: "#999" }}>已隐藏 {dismissedFindingIds.size} 条</span>
                {onClearDismissed && (
                  <span onClick={onClearDismissed} style={{ cursor: "pointer", color: "#e74c3c", fontSize: 10 }}>
                    重置
                  </span>
                )}
              </>
            )}
          </div>
        )}
        {/* 底部元信息 */}
        <div style={{ padding: "4px 8px", fontSize: 10, color: "#999", display: "flex", gap: 12 }}>
          <span>🔀 {analysisResult.topology}</span>
          <span>📊 {analysisResult.complexity}</span>
          {analysisResult.total_cost_usd > 0 && <span>💰 ${analysisResult.total_cost_usd.toFixed(4)}</span>}
        </div>
      </div>
    );
  };

  // =======================================================================
  // Render
  // =======================================================================

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", fontSize: 13 }}>
      {/* 标题 */}
      <div style={{ fontWeight: 600, padding: "12px 12px 0", marginBottom: 4 }}>📌 上下文提示板</div>

      {/* 分析中: 进度条 */}
      {analyzing && <ProgressBar agents={agentStates} active={true} />}

      {/* 分析完成摘要 */}
      {!analyzing && analysisResult && (
        <ProgressBar agents={agentStates} active={false} findingsCount={analysisResult.findings.length} />
      )}

      {/* 内容区: 便签 或 暖场 */}
      <div style={{ flex: 1, overflow: "auto", padding: "8px 10px" }}>
        {analysisResult && !analyzing ? (
          visibleNotes.length > 0 ? (
            visibleNotes.map(renderNote)
          ) : (
            <div style={{ padding: 24, color: "#999", fontSize: 13, textAlign: "center" }}>
              所有便签已撕掉 🗑️<br />
              <span style={{ fontSize: 11 }}>切换章节后重新生成</span>
            </div>
          )
        ) : !analyzing ? (
          /* 暖场便签 */
          <>{WARMUP_NOTES.map((note) => (
            <div
              key={note.id}
              style={{
                background: note.color,
                borderRadius: 6,
                padding: "10px 12px",
                marginBottom: 8,
                border: "1px solid rgba(0,0,0,0.06)",
                fontSize: 12,
                lineHeight: 1.6,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 6 }}>
                <span>{note.icon}</span>
                <span style={{ fontWeight: 600, fontSize: 13 }}>{note.title}</span>
              </div>
              {note.lines.map((line, i) => (
                <div key={i} style={{ paddingLeft: 18, color: line.startsWith("✓") ? "#34a853" : line.startsWith("·") ? "#666" : "#444", fontSize: 11, marginBottom: 2 }}>
                  {line || " "}
                </div>
              ))}
            </div>
          ))}</>
        ) : null}
      </div>
    </div>
  );
};
