/**
 * 分析触发面板 — Narrative Mind v4.0
 *
 * Phase E: 触发 Agent 分析，显示结果摘要。
 */

import { useState } from "react";
import { runAnalysis } from "../api";
import type { AnalysisOutput } from "../api";

interface AnalysisPanelProps {
  /** 当前章节 ID */
  chapterId: string;
  /** 分析结果回调 */
  onResult?: (result: AnalysisOutput) => void;
  /** 错误回调 */
  onError?: (error: string) => void;
}

const TASK_TYPES = [
  { key: "pad_compute", label: "PAD 情感分析", icon: "🎭" },
  { key: "entity_extract", label: "实体提取", icon: "👤" },
  { key: "action_infer", label: "动作推理", icon: "⚡" },
  { key: "rule_check", label: "规则检查", icon: "📋" },
  { key: "foreshadow_detect", label: "伏笔检测", icon: "🔍" },
  { key: "style_check", label: "文风检查", icon: "✒️" },
  { key: "theme_extract", label: "主题提取", icon: "🎯" },
  { key: "economy_check", label: "经济性检查", icon: "📊" },
  { key: "scene_analysis", label: "场景分析", icon: "🎬" },
];

export function AnalysisPanel({ chapterId, onResult, onError }: AnalysisPanelProps) {
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState<AnalysisOutput | null>(null);

  const handleAnalyze = async (taskType: string) => {
    setLoading(true);
    try {
      const result = await runAnalysis(chapterId, taskType);
      setLastResult(result);
      onResult?.(result);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      onError?.(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="analysis-panel"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        padding: 12,
        fontSize: 13,
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 4 }}>
        🤖 Agent 分析
      </div>

      {/* 任务选择按钮组 */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 6,
        }}
      >
        {TASK_TYPES.map((tt) => (
          <button
            key={tt.key}
            onClick={() => handleAnalyze(tt.key)}
            disabled={loading || !chapterId}
            style={{
              padding: "4px 10px",
              fontSize: 12,
              border: "1px solid #ddd",
              borderRadius: 4,
              background: loading ? "#f5f5f5" : "#fff",
              cursor: loading ? "wait" : "pointer",
              opacity: loading ? 0.6 : 1,
            }}
          >
            {tt.icon} {tt.label}
          </button>
        ))}
      </div>

      {/* 加载指示 */}
      {loading && (
        <div style={{ color: "#4285f4", fontSize: 12 }}>
          ⏳ 正在分析...
        </div>
      )}

      {/* 结果摘要 */}
      {lastResult && !loading && (
        <div
          style={{
            marginTop: 8,
            padding: 8,
            background: "#f0f7ff",
            borderRadius: 4,
            fontSize: 12,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4 }}>
            ✅ 分析完成
          </div>
          <div>拓扑: {lastResult.topology}</div>
          <div>复杂度: {lastResult.complexity}</div>
          <div>Agent 输出: {lastResult.agent_outputs.length} 条</div>
          {lastResult.agent_outputs.map((ao) => (
            <div
              key={ao.agent_id}
              style={{
                marginTop: 4,
                padding: "4px 8px",
                background: "#fff",
                borderRadius: 3,
                borderLeft: "3px solid #4285f4",
              }}
            >
              <strong>{ao.agent_name}</strong>
              <pre
                style={{
                  margin: "4px 0 0",
                  fontSize: 11,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                  maxHeight: 120,
                  overflow: "auto",
                }}
              >
                {ao.output.substring(0, 500)}
                {ao.output.length > 500 && "..."}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
