import React from "react";

/**
 * LeftSidebar — 左侧导航栏
 *
 * Phase A 骨架：图标占位，无交互逻辑。
 * Phase E 加入实际导航功能和面板切换。
 */

const ICONS = [
  { label: "项目", icon: "📁" },
  { label: "大纲", icon: "📋" },
  { label: "搜索", icon: "🔍" },
  { label: "Agent", icon: "🤖" },
  { label: "设置", icon: "⚙️" },
];

const LeftSidebar: React.FC = () => {
  return (
    <div className="left-sidebar">
      {ICONS.map((item) => (
        <div
          key={item.label}
          className={`sidebar-icon${item.label === "项目" ? " active" : ""}`}
          title={item.label}
        >
          {item.icon}
        </div>
      ))}
    </div>
  );
};

export default LeftSidebar;
