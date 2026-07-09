/**
 * 分析进度条 — Narrative Mind v4.0
 *
 * 水平进度条，显示 Agent 执行进度（done / total）。
 * 分析中显示蓝色动画，完成后显示摘要。
 */

import type { AgentState } from "../types";

interface ProgressBarProps {
  agents: AgentState[];
  /** 是否正在分析 */
  active: boolean;
  /** 完成后的发现总数 */
  findingsCount?: number;
}

export function ProgressBar({ agents, active, findingsCount }: ProgressBarProps) {
  if (!active && agents.length === 0) return null;

  const total = agents.length || 9;
  const done = agents.filter((a) => a.status === "done").length;
  const running = agents.find((a) => a.status === "running");
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  // 分析完成
  if (!active && done > 0) {
    return (
      <div style={containerStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ color: "#34a853", fontWeight: 600 }}>✅ 分析完成</span>
          <span style={{ color: "#666", fontSize: 12 }}>
            {findingsCount !== undefined ? `${findingsCount} 条发现` : `${done}/${total} Agent`}
          </span>
        </div>
      </div>
    );
  }

  // 分析中
  return (
    <div style={containerStyle}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <span style={spinnerStyle}>⏳</span>
        <span style={{ fontSize: 13, color: "#4285f4", fontWeight: 500 }}>
          分析中… {done}/{total}
        </span>
        {running && (
          <span style={{ fontSize: 12, color: "#888" }}>
            · {running.agent_name} 运行中
          </span>
        )}
      </div>
      <div style={trackStyle}>
        <div
          style={{
            ...barStyle,
            width: `${Math.max(pct, 2)}%`,
            transition: "width 0.4s ease",
          }}
        />
        {/* Agent 分段标记 */}
        {agents.map((agent, i) => {
          const left = (i / total) * 100;
          return (
            <div
              key={agent.agent_id}
              title={`${agent.agent_name}: ${agent.status}`}
              style={{
                position: "absolute",
                left: `${left}%`,
                top: -3,
                width: 8,
                height: 8,
                borderRadius: "50%",
                background:
                  agent.status === "done"
                    ? "#34a853"
                    : agent.status === "running"
                      ? "#4285f4"
                      : agent.status === "error"
                        ? "#ea4335"
                        : "#ccc",
                border: "1px solid #fff",
                transition: "background 0.3s",
              }}
            />
          );
        })}
      </div>
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  padding: "10px 12px",
  borderBottom: "1px solid #e0e0e0",
  background: "#f8f9ff",
};

const spinnerStyle: React.CSSProperties = {
  display: "inline-block",
  animation: "spin 1s linear infinite",
  fontSize: 14,
};

const trackStyle: React.CSSProperties = {
  position: "relative",
  height: 6,
  background: "#e0e0e0",
  borderRadius: 3,
  overflow: "visible",
};

const barStyle: React.CSSProperties = {
  height: "100%",
  background: "linear-gradient(90deg, #4285f4, #34a853)",
  borderRadius: 3,
};
