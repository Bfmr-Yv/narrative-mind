import React from "react";

/**
 * TitleBar — 顶部标题栏
 *
 * 显示项目名称和 Agent 状态指示器。
 * Phase A 骨架，Phase E 加入项目名动态读取和 Agent 实时状态。
 */
const TitleBar: React.FC = () => {
  return (
    <div className="titlebar">
      <div className="titlebar-left">
        <span>📖 Narrative Mind v4.0</span>
        <span style={{ fontSize: "11px", color: "#666" }}>
          — AI 辅助小说创作
        </span>
      </div>
      <div className="titlebar-agent-status">
        <span className="agent-indicator inactive" title="Agent 空闲" />
        <span>Agents idle</span>
      </div>
    </div>
  );
};

export default TitleBar;
