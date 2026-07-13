/**
 * ImportPanel — Phase B: 导入模式
 *
 * 粘贴已有小说文本 → AI 提取设定 → 预览 → 确认导入。
 */

import { useState, useCallback, type FC } from "react";
import type { ProjectContext } from "../types";
import { runImportAnalysis } from "../api/analysis";

// ── Props ──

interface Props {
  projectId: string;
  onImport: (ctx: ProjectContext) => Promise<void>;
  onClose: () => void;
}

// ── 样式 ──

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "4px 6px", fontSize: 12,
  border: "1px solid #d0d0d0", borderRadius: 3, outline: "none",
};

const textareaStyle: React.CSSProperties = {
  ...inputStyle, minHeight: 200, resize: "vertical", fontFamily: "monospace",
};

const btnPrimary: React.CSSProperties = {
  padding: "6px 16px", fontSize: 13, border: "none",
  borderRadius: 4, background: "#4285f4", color: "#fff", cursor: "pointer",
};

const btnSecondary: React.CSSProperties = {
  padding: "6px 16px", fontSize: 13, border: "1px solid #ccc",
  borderRadius: 4, background: "#fff", cursor: "pointer",
};

const btnSuccess: React.CSSProperties = {
  padding: "6px 16px", fontSize: 13, border: "none",
  borderRadius: 4, background: "#34a853", color: "#fff", cursor: "pointer",
};

const labelStyle: React.CSSProperties = {
  fontSize: 12, fontWeight: 600, marginBottom: 4, display: "block",
};

const sectionStyle: React.CSSProperties = {
  marginBottom: 12,
};

// ── 组件 ──

export const ImportPanel: FC<Props> = ({ projectId, onImport, onClose }) => {
  const [text, setText] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<ProjectContext | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState("");

  const handleAnalyze = useCallback(async () => {
    if (!text.trim()) return;
    setAnalyzing(true);
    setError(null);
    setResult(null);
    setProgress("正在分块...");

    try {
      // 显示分块信息
      const chunks = Math.ceil(text.length / 3000);
      setProgress(`分块完成，共 ${chunks} 块。正在提取中...`);

      const ctx = await runImportAnalysis(text, projectId);
      setResult(ctx);
      setProgress("提取完成！请预览结果。");
    } catch (e) {
      setError(`导入分析失败: ${e}`);
      setProgress("");
    } finally {
      setAnalyzing(false);
    }
  }, [text, projectId]);

  const handleConfirm = useCallback(async () => {
    if (!result) return;
    await onImport(result);
  }, [result, onImport]);

  // ── 结果预览 ──

  const renderPreview = () => {
    if (!result) return null;
    const wr = result.world_rules;
    const po = result.plot_outline;
    const sg = result.style_guide;
    const tm = result.theme_map;

    return (
      <div style={{ marginTop: 12 }}>
        <h3 style={{ fontSize: 14, marginBottom: 8 }}>📋 提取结果预览</h3>

        {wr && (
          <div style={sectionStyle}>
            <strong style={labelStyle}>世界观</strong>
            <div style={{ fontSize: 12, color: "#555", maxHeight: 120, overflow: "auto", background: "#f9f9f9", padding: 6, borderRadius: 3 }}>
              {wr.magic_system && <p>力量体系: {wr.magic_system}</p>}
              {wr.technology_level && <p>科技水平: {wr.technology_level}</p>}
              {wr.social_structure && <p>社会结构: {wr.social_structure}</p>}
              {wr.geography && <p>地理: {wr.geography}</p>}
              {wr.custom_rules.length > 0 && <p>自定义规则: {wr.custom_rules.join("、")}</p>}
            </div>
          </div>
        )}

        {result.character_profiles.length > 0 && (
          <div style={sectionStyle}>
            <strong style={labelStyle}>角色 ({result.character_profiles.length} 个)</strong>
            <div style={{ fontSize: 12, color: "#555", maxHeight: 120, overflow: "auto", background: "#f9f9f9", padding: 6, borderRadius: 3 }}>
              {result.character_profiles.map((cp, i) => (
                <span key={i} style={{ display: "inline-block", margin: "2px 6px 2px 0", padding: "2px 6px", background: "#e8f0fe", borderRadius: 3 }}>
                  {cp.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {po && (
          <div style={sectionStyle}>
            <strong style={labelStyle}>情节大纲</strong>
            <div style={{ fontSize: 12, color: "#555", maxHeight: 120, overflow: "auto", background: "#f9f9f9", padding: 6, borderRadius: 3 }}>
              <p>主线: {po.main_plot.substring(0, 200)}</p>
              <p>支线: {po.subplots.length} 条 | 伏笔: {po.foreshadow_plan.length} 条 | 章节: {po.chapter_outlines.length} 章</p>
            </div>
          </div>
        )}

        {sg && (
          <div style={sectionStyle}>
            <strong style={labelStyle}>文风</strong>
            <div style={{ fontSize: 12, color: "#555", maxHeight: 80, overflow: "auto", background: "#f9f9f9", padding: 6, borderRadius: 3 }}>
              <p>{sg.prose_style}</p>
            </div>
          </div>
        )}

        {tm && (
          <div style={sectionStyle}>
            <strong style={labelStyle}>主题</strong>
            <div style={{ fontSize: 12, color: "#555" }}>
              {tm.primary_themes.length > 0 && <span>主要主题: {tm.primary_themes.join(", ")}</span>}
              {tm.imagery_motifs.length > 0 && <span> | 意象: {tm.imagery_motifs.join(", ")}</span>}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "#fff" }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 12px",
        borderBottom: "1px solid #e0e0e0",
      }}>
        <span style={{ fontSize: 14, fontWeight: 700 }}>📥 导入已有作品</span>
        <span style={{ flex: 1 }} />
        <button style={btnSecondary} onClick={onClose}>✕ 关闭</button>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflow: "auto", padding: 12 }}>
        <p style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>
          粘贴你已有的小说文本（或其中片段），AI 将自动提取世界观规则、角色档案、情节结构和文风特征。
        </p>

        <textarea
          style={textareaStyle}
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="在此粘贴小说文本..."
          disabled={analyzing}
        />

        <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center" }}>
          <button
            style={btnPrimary}
            onClick={handleAnalyze}
            disabled={analyzing || !text.trim()}
          >
            {analyzing ? "⏳ 分析中..." : "🚀 开始导入分析"}
          </button>
          {progress && (
            <span style={{ fontSize: 12, color: "#666" }}>{progress}</span>
          )}
        </div>

        {error && (
          <div style={{ marginTop: 8, padding: 8, background: "#fdecea", borderRadius: 4, fontSize: 12, color: "#e74c3c" }}>
            {error}
          </div>
        )}

        {renderPreview()}
      </div>

      {/* Footer */}
      {result && (
        <div style={{
          display: "flex", gap: 8, padding: "8px 12px",
          borderTop: "1px solid #e0e0e0", background: "#fafafa",
        }}>
          <button style={btnSecondary} onClick={onClose}>取消</button>
          <span style={{ flex: 1 }} />
          <button style={btnSuccess} onClick={handleConfirm}>
            ✅ 确认导入
          </button>
        </div>
      )}
    </div>
  );
};
