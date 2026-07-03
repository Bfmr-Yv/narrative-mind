/**
 * 分析状态栏 — Narrative Mind v4.0
 *
 * Phase E: 显示 9 个 Agent 的实时运行状态。
 */

import type { AgentState } from "../types";

interface StatusBarProps {
  /** 各 Agent 的运行状态 */
  agents: AgentState[];
  /** 当前拓扑描述 */
  topology?: string;
  /** 当前复杂度 */
  complexity?: string;
  /** 总成本 */
  totalCost?: number;
}

const STATUS_ICONS: Record<string, string> = {
  idle: "○",
  running: "◐",
  done: "●",
  error: "✗",
};

const STATUS_COLORS: Record<string, string> = {
  idle: "#999",
  running: "#4285f4",
  done: "#34a853",
  error: "#ea4335",
};

export function StatusBar({ agents, topology, complexity, totalCost }: StatusBarProps) {
  return (
    <div
      className="analysis-status-bar"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "6px 16px",
        fontSize: 13,
        color: "#666",
        borderTop: "1px solid #e0e0e0",
        background: "#fafafa",
        fontFamily: 'system-ui, -apple-system, sans-serif',
        overflow: "auto",
        whiteSpace: "nowrap",
      }}
    >
      {/* Agent 状态指示器 */}
      {agents.map((agent) => (
        <span
          key={agent.agent_id}
          title={`${agent.agent_name}: ${agent.status}${agent.error ? ` (${agent.error})` : ""}`}
          style={{ cursor: "default" }}
        >
          <span style={{ color: STATUS_COLORS[agent.status] }}>
            {STATUS_ICONS[agent.status]}
          </span>{" "}
          {agent.agent_name}
          {agent.status === "running" && (
            <span style={{ color: "#4285f4", marginLeft: 2 }}>
              {agent.progress}%
            </span>
          )}
        </span>
      ))}

      {/* 分隔 */}
      {agents.length > 0 && <span style={{ color: "#ddd" }}>|</span>}

      {/* 拓扑信息 */}
      {topology && (
        <span title="当前执行拓扑">
          🔀 {topology}
        </span>
      )}

      {/* 复杂度 */}
      {complexity && (
        <span title="任务复杂度">
          📊 {complexity}
        </span>
      )}

      {/* 成本 */}
      {totalCost !== undefined && totalCost > 0 && (
        <span title="累计成本" style={{ marginLeft: "auto" }}>
          💰 ${totalCost.toFixed(4)}
        </span>
      )}
    </div>
  );
}
