import React from "react";

const App: React.FC = () => {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      color: "#6b7280",
      fontSize: "14px",
    }}>
      <div style={{ textAlign: "center" }}>
        <h1 style={{ fontSize: "24px", marginBottom: "8px", color: "#1f2937" }}>
          Narrative Mind
        </h1>
        <p>v4.0 — AI 辅助小说创作系统</p>
        <p style={{ marginTop: "16px", fontSize: "12px", color: "#9ca3af" }}>
          脚手架就绪 · Phase A 进行中
        </p>
      </div>
    </div>
  );
};

export default App;
