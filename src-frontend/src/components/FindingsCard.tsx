/**
 * 结构化发现卡片 — Narrative Mind v4.0
 *
 * 将 AgentFinding 渲染为可读的卡片：
 * 严重度图标 + 标题 + 描述 + 建议 + 原文引用 + 来源信息
 */

import type { AgentFinding, Severity } from "../types";

interface FindingsCardProps {
  finding: AgentFinding;
  agentName?: string;
  onDismiss?: (id: string) => void;
  onSnooze?: (id: string) => void;
  isDismissed?: boolean;
}

const SEVERITY_CONFIG: Record<Severity, { icon: string; label: string; color: string; bg: string }> = {
  Info: { icon: "ℹ️", label: "信息", color: "#4285f4", bg: "#e8f0fe" },
  Warn: { icon: "⚠️", label: "注意", color: "#f9ab00", bg: "#fef7e0" },
  Critical: { icon: "🔴", label: "严重", color: "#ea4335", bg: "#fce8e6" },
};

export function FindingsCard({ finding, agentName, onDismiss, onSnooze, isDismissed }: FindingsCardProps) {
  const sev = SEVERITY_CONFIG[finding.severity] ?? SEVERITY_CONFIG.Info;

  return (
    <div
      style={{
        margin: "8px 0",
        borderLeft: `3px solid ${sev.color}`,
        borderRadius: "4px 0 0 4px",
        background: "#fff",
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        overflow: "hidden",
      }}
    >
      {/* 标题行 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "8px 10px",
          background: sev.bg,
          borderBottom: "1px solid #f0f0f0",
        }}
      >
        <span style={{ fontSize: 14 }}>{sev.icon}</span>
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: sev.color,
            textTransform: "uppercase",
            background: "#fff",
            padding: "1px 6px",
            borderRadius: 3,
          }}
        >
          {sev.label}
        </span>
        <span style={{ fontSize: 13, fontWeight: 600, flex: 1 }}>{finding.title}</span>
      </div>

      {/* 问题描述 */}
      <div style={{ padding: "8px 10px", fontSize: 13, lineHeight: 1.6, color: "#333" }}>
        {finding.description}
      </div>

      {/* 修改建议 */}
      {finding.suggestion && (
        <div
          style={{
            margin: "0 10px 8px",
            padding: "6px 10px",
            background: "#f0f7e8",
            borderRadius: 4,
            fontSize: 12,
            lineHeight: 1.5,
            color: "#2e7d32",
          }}
        >
          <span style={{ fontWeight: 600 }}>💡 建议：</span>
          {finding.suggestion}
        </div>
      )}

      {/* 底部元信息 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "4px 10px 6px",
          fontSize: 11,
          color: "#999",
          borderTop: "1px solid #f5f5f5",
          background: "#fafafa",
        }}
      >
        <span>{(agentName ?? finding.agent_id).replace("Agent", "").trim()}</span>
        {finding.timestamp && (
          <>
            <span>·</span>
            <span>{new Date(finding.timestamp).toLocaleString("zh-CN", { hour: "2-digit", minute: "2-digit" })}</span>
          </>
        )}
        <span style={{ flex: 1 }} />
        {onDismiss && !isDismissed && (
          <span style={{ display: "flex", gap: 4 }}>
            <span
              title="暂隐（本次隐藏）"
              onClick={(e) => { e.stopPropagation(); onSnooze?.(finding.id); }}
              style={{ cursor: "pointer", fontSize: 12, opacity: 0.6 }}
            >
              ⏳
            </span>
            <span
              title="忽略（永久隐藏）"
              onClick={(e) => { e.stopPropagation(); onDismiss(finding.id); }}
              style={{ cursor: "pointer", fontSize: 12, opacity: 0.6 }}
            >
              ❌
            </span>
          </span>
        )}
      </div>
    </div>
  );
}
