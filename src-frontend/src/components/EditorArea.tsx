import React from "react";

/**
 * EditorArea — Monaco 编辑器占位区域
 *
 * Phase A 骨架：显示占位提示。
 * Phase E 嵌入 Monaco Editor + 装饰系统。
 */
const EditorArea: React.FC = () => {
  return (
    <div className="editor-area">
      <div className="editor-placeholder">
        <div className="editor-placeholder-inner">
          <h2>Narrative Mind</h2>
          <p>Monaco Editor 将在 Phase E 集成</p>
          <p style={{ marginTop: "16px", fontSize: "11px" }}>
            Ctrl+O 打开项目 · Ctrl+N 新建章节 · Ctrl+S 保存
          </p>
        </div>
      </div>
      {/* 底部状态栏 */}
      <div className="statusbar">
        <div className="statusbar-left">
          <span>无打开项目</span>
          <span>字数: 0</span>
        </div>
        <div className="statusbar-right">
          <span>UTF-8</span>
          <span>简体中文</span>
          <span>第 0 章</span>
        </div>
      </div>
    </div>
  );
};

export default EditorArea;
