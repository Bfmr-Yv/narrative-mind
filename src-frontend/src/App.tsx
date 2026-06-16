import React from "react";
import TitleBar from "./components/TitleBar";
import LeftSidebar from "./components/LeftSidebar";
import EditorArea from "./components/EditorArea";
import "./App.css";

/**
 * App — Narrative Mind v4.0 根组件
 *
 * Phase A 布局骨架：
 * - 顶部标题栏（TitleBar）
 * - 左侧导航栏（LeftSidebar）
 * - 中央编辑器区域（EditorArea，Monaco 占位）
 *
 * Phase E 后替换为完整 Monaco + Agent Panel。
 */
const App: React.FC = () => {
  return (
    <div className="app-container">
      <TitleBar />
      <div className="main-area">
        <LeftSidebar />
        <EditorArea />
      </div>
    </div>
  );
};

export default App;
