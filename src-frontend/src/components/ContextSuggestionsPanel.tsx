/**
 * ContextSuggestionsPanel — Phase C: 上下文变更建议面板
 *
 * 展示反思 Agent 产出的 ProjectContext 修改建议（diff 形式）。
 */

import { useState, useCallback, type FC } from "react";
import type { ContextSuggestion, ProjectContext } from "../types";

// ── Props ──

interface Props {
  suggestions: ContextSuggestion[];
  projectContext: ProjectContext | null;
  onAccept: (suggestion: ContextSuggestion) => Promise<void>;
  onReject: (suggestion: ContextSuggestion) => void;
  onClose: () => void;
}

// ── 样式 ──

const btnPrimary: React.CSSProperties = {
  padding: "4px 12px", fontSize: 12, border: "none",
  borderRadius: 3, background: "#4285f4", color: "#fff", cursor: "pointer",
};

const btnSecondary: React.CSSProperties = {
  padding: "4px 12px", fontSize: 12, border: "1px solid #ccc",
  borderRadius: 3, background: "#fff", cursor: "pointer",
};

const btnSuccess: React.CSSProperties = {
  ...btnPrimary, background: "#34a853",
};

const btnDanger: React.CSSProperties = {
  ...btnPrimary, background: "#e74c3c",
};

// ── 置信度颜色 ──

function confidenceColor(c: number): string {
  if (c >= 0.8) return "#34a853";
  if (c >= 0.5) return "#f9ab00";
  return "#ea4335";
}

// ── 组件 ──

export const ContextSuggestionsPanel: FC<Props> = ({ suggestions, onAccept, onReject, onClose }) => {
  const [acceptedIds, setAcceptedIds] = useState<Set<string>>(new Set());
  const [rejectedIds, setRejectedIds] = useState<Set<string>>(new Set());
  const [processingId, setProcessingId] = useState<string | null>(null);

  const handleAccept = useCallback(async (s: ContextSuggestion) => {
    setProcessingId(s.id);
    try {
      await onAccept(s);
      setAcceptedIds(prev => new Set(prev).add(s.id));
    } catch (e) {
      console.error("Accept failed:", e);
    } finally {
      setProcessingId(null);
    }
  }, [onAccept]);

  const handleReject = useCallback((s: ContextSuggestion) => {
    setRejectedIds(prev => new Set(prev).add(s.id));
    onReject(s);
  }, [onReject]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "#fff" }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 12px",
        borderBottom: "1px solid #e0e0e0",
      }}>
        <span style={{ fontSize: 14, fontWeight: 700 }}>
          📝 上下文修订建议 ({suggestions.length} 条)
        </span>
        <span style={{ flex: 1 }} />
        <button style={btnSecondary} onClick={onClose}>✕ 关闭</button>
      </div>

      {/* List */}
      <div style={{ flex: 1, overflow: "auto", padding: 12 }}>
        {suggestions.map((s) => {
          const isAccepted = acceptedIds.has(s.id);
          const isRejected = rejectedIds.has(s.id);
          const isProcessing = processingId === s.id;

          return (
            <div key={s.id} style={{
              border: `1px solid ${isAccepted ? "#34a853" : isRejected ? "#e0e0e0" : "#d0d0d0"}`,
              borderRadius: 6, padding: 10, marginBottom: 10,
              opacity: isRejected ? 0.4 : 1,
              background: isAccepted ? "#f0f7e8" : "#fff",
            }}>
              {/* 字段路径 + 置信度 */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <code style={{
                  fontSize: 11, background: "#f0f0f0", padding: "2px 6px",
                  borderRadius: 3, color: "#555", flex: 1,
                }}>
                  {s.field_path}
                </code>
                <div style={{
                  display: "flex", alignItems: "center", gap: 4, fontSize: 11,
                }}>
                  <div style={{
                    width: 40, height: 6, background: "#eee", borderRadius: 3, overflow: "hidden",
                  }}>
                    <div style={{
                      width: `${Math.round(s.confidence * 100)}%`, height: "100%",
                      background: confidenceColor(s.confidence), borderRadius: 3,
                    }} />
                  </div>
                  <span style={{ color: confidenceColor(s.confidence), fontWeight: 600 }}>
                    {Math.round(s.confidence * 100)}%
                  </span>
                </div>
              </div>

              {/* Diff: 当前值 → 建议值 */}
              <div style={{ marginBottom: 6, fontSize: 12 }}>
                <div style={{ color: "#e74c3c", textDecoration: "line-through", marginBottom: 2 }}>
                  {s.current_value || "（空）"}
                </div>
                <div style={{ color: "#34a853", fontWeight: 600 }}>
                  → {s.suggested_value}
                </div>
              </div>

              {/* 证据引用 */}
              {s.evidence && (
                <blockquote style={{
                  fontSize: 11, color: "#888", borderLeft: "2px solid #4285f4",
                  margin: "6px 0", padding: "2px 8px", fontStyle: "italic",
                }}>
                  "{s.evidence}"
                </blockquote>
              )}

              {/* 操作按钮 */}
              <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
                <button
                  style={btnSuccess}
                  disabled={isAccepted || isRejected || isProcessing}
                  onClick={() => handleAccept(s)}
                  title="接受此修改建议"
                >
                  {isProcessing ? "⏳" : isAccepted ? "✅ 已应用" : "✅ 接受"}
                </button>
                <button
                  style={btnDanger}
                  disabled={isAccepted || isRejected}
                  onClick={() => handleReject(s)}
                  title="拒绝此修改建议"
                >
                  {isRejected ? "❌ 已拒绝" : "❌ 拒绝"}
                </button>
              </div>
            </div>
          );
        })}

        {suggestions.length === 0 && (
          <div style={{ textAlign: "center", color: "#ccc", padding: 40, fontSize: 13 }}>
            暂无上下文修订建议
          </div>
        )}
      </div>
    </div>
  );
};
