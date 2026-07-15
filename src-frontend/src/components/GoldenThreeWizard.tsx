/**
 * GoldenThreeWizard — Phase D: 黄金三章引导
 *
 * 4 步交互: 前置检查 → Ch1 → Ch2 → Ch3 → 完成保存
 */

import { useState, useCallback, useEffect, type FC } from "react";
import type { ProjectContext } from "../types";
import { startGoldenThree, continueGoldenThree, finalizeGoldenThree, resumeGoldenThree, createChapter } from "../api";
import type { GoldenThreeOutput } from "../api/analysis";

// ── Props ──

interface Props {
  projectId: string;
  projectContext: ProjectContext | null;
  onComplete: () => Promise<void>;
  onClose: () => void;
}

// ── 样式 ──

const btnPrimary: React.CSSProperties = {
  padding: "6px 16px", fontSize: 13, border: "none",
  borderRadius: 4, background: "#4285f4", color: "#fff", cursor: "pointer",
};

const btnSecondary: React.CSSProperties = {
  padding: "6px 16px", fontSize: 13, border: "1px solid #ccc",
  borderRadius: 4, background: "#fff", cursor: "pointer",
};

const btnSuccess: React.CSSProperties = {
  ...btnPrimary, background: "#34a853",
};

const btnWarning: React.CSSProperties = {
  ...btnPrimary, background: "#f9ab00",
};

// ── 前置条件检查 ──

function checkPrereqs(ctx: ProjectContext | null): string[] {
  if (!ctx) return ["项目创作上下文未初始化"];
  const missing: string[] = [];
  if (!ctx.world_rules || (!ctx.world_rules.magic_system && ctx.world_rules.custom_rules.length === 0))
    missing.push("世界观规则");
  if (ctx.character_profiles.length === 0)
    missing.push("至少一个角色档案");
  if (!ctx.plot_outline || !ctx.plot_outline.main_plot)
    missing.push("情节大纲（主线）");
  return missing;
}

// ── 组件 ──

export const GoldenThreeWizard: FC<Props> = ({ projectId, projectContext, onComplete, onClose }) => {
  const [step, setStep] = useState(0); // 0=prereq, 1-3=chapters, 4=done
  const [sessionId, setSessionId] = useState("");
  const [chapters, setChapters] = useState({ ch1: "", ch2: "", ch3: "" });
  const [notes, setNotes] = useState<string[]>([]);
  const [generating, setGenerating] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState("");
  const [error, setError] = useState<string | null>(null);

  const missing = checkPrereqs(projectContext);

  // ── 恢复未完成会话 ──
  const [resuming, setResuming] = useState(false);
  const [resumableSession, setResumableSession] = useState<{ session_id: string; stage: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    resumeGoldenThree(projectId).then(session => {
      if (!cancelled && session) {
        setResumableSession({ session_id: session.session_id, stage: session.stage });
      }
    }).catch(() => { /* 静默失败 */ });
    return () => { cancelled = true; };
  }, [projectId]);

  const handleResume = useCallback(async () => {
    if (!resumableSession) return;
    setResuming(true);
    setSessionId(resumableSession.session_id);
    // 继续生成下一章（不传 edited_chapter，不传 regenerate）
    setGenerating(true);
    try {
      const result = await continueGoldenThree(resumableSession.session_id, undefined, false);
      setChapters(prev => {
        const next = { ...prev };
        if (result.stage === 2) next.ch2 = result.chapter_text;
        if (result.stage === 3) next.ch3 = result.chapter_text;
        return next;
      });
      setNotes(result.consistency_notes);
      setStep(result.stage);
    } catch (e) {
      setError(`恢复失败: ${e}`);
      setResumableSession(null);
    } finally {
      setGenerating(false);
      setResuming(false);
    }
  }, [resumableSession]);

  // ── 开始生成 ──
  const handleStart = useCallback(async () => {
    setGenerating(true);
    try {
      const result = await startGoldenThree(projectId);
      setSessionId(result.session_id);
      setChapters({ ch1: result.chapter_text, ch2: "", ch3: "" });
      setNotes(result.consistency_notes);
      setStep(1);
    } catch (e) {
      setError(`生成失败: ${e}`);
    } finally {
      setGenerating(false);
    }
  }, [projectId]);

  // ── 继续生成下一章 ──
  const handleContinue = useCallback(async () => {
    if (!sessionId) return;
    setGenerating(true);
    try {
      const edited = editing ? editText : undefined;
      setEditing(false);
      const result = await continueGoldenThree(sessionId, edited);
      setChapters(prev => {
        const next = { ...prev };
        if (result.stage === 2) next.ch2 = result.chapter_text;
        if (result.stage === 3) next.ch3 = result.chapter_text;
        return next;
      });
      setNotes(result.consistency_notes);
      setStep(result.stage);
    } catch (e) {
      setError(`生成失败: ${e}`);
    } finally {
      setGenerating(false);
    }
  }, [sessionId, editing, editText]);

  // ── 重新生成当前章 ──
  const handleRegenerate = useCallback(async () => {
    if (!sessionId) return;
    setGenerating(true);
    try {
      const edited = editing ? editText : undefined;
      setEditing(false);
      const result = await continueGoldenThree(sessionId, edited, true);
      setChapters(prev => {
        const next = { ...prev };
        if (result.stage === 1) next.ch1 = result.chapter_text;
        if (result.stage === 2) next.ch2 = result.chapter_text;
        if (result.stage === 3) next.ch3 = result.chapter_text;
        return next;
      });
      setNotes(result.consistency_notes);
      // stage 不变，因为是重新生成
    } catch (e) {
      setError(`重新生成失败: ${e}`);
    } finally {
      setGenerating(false);
    }
  }, [sessionId, editing, editText]);

  // ── 完成 → 保存三章 ──
  const handleFinalize = useCallback(async () => {
    if (!sessionId) return;
    setGenerating(true);
    try {
      const result = await finalizeGoldenThree(sessionId);
      await createChapter(projectId, "第1章", result.chapter_1);
      await createChapter(projectId, "第2章", result.chapter_2);
      await createChapter(projectId, "第3章", result.chapter_3);
      setStep(4);
      await onComplete();
    } catch (e) {
      setError(`保存失败: ${e}`);
    } finally {
      setGenerating(false);
    }
  }, [sessionId, projectId, onComplete]);

  // ── 当前章文本 ──
  const currentChapter = step === 1 ? chapters.ch1 : step === 2 ? chapters.ch2 : step === 3 ? chapters.ch3 : "";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "#fff" }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 12px",
        borderBottom: "1px solid #e0e0e0",
      }}>
        <span style={{ fontSize: 14, fontWeight: 700 }}>🚀 一键黄金三章</span>
        <span style={{ flex: 1 }} />
        <button style={btnSecondary} onClick={onClose}>✕ 关闭</button>
      </div>

      {/* 进度条 */}
      {step > 0 && step < 4 && (
        <div style={{ padding: "8px 12px", borderBottom: "1px solid #f0f0f0" }}>
          <div style={{ display: "flex", gap: 0 }}>
            {[1, 2, 3].map(n => (
              <div key={n} style={{
                flex: 1, textAlign: "center", padding: "4px 0", fontSize: 12,
                background: step >= n ? "#e8f5e9" : "#f5f5f5",
                color: step >= n ? "#34a853" : "#ccc",
                fontWeight: step === n ? 600 : 400,
                borderRadius: n === 1 ? "4px 0 0 4px" : n === 3 ? "0 4px 4px 0" : 0,
              }}>
                {step > n ? `✅ 第${n}章` : step === n ? `📝 第${n}章` : `第${n}章`}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Body */}
      <div style={{ flex: 1, overflow: "auto", padding: 12 }}>
        {/* 错误提示 toast */}
        {error && (
          <div style={{
            padding: "8px 12px", background: "#fce8e6", color: "#c5221f",
            borderRadius: 4, marginBottom: 8, fontSize: 12, display: "flex", alignItems: "center", gap: 8,
          }}>
            <span style={{ flex: 1 }}>❌ {error}</span>
            <button onClick={() => setError(null)} style={{
              border: "none", background: "transparent", cursor: "pointer",
              fontSize: 14, color: "#c5221f",
            }}>✕</button>
          </div>
        )}
        {/* Step 0: 前置检查 */}
        {step === 0 && (
          <div style={{ textAlign: "center", padding: 40 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📖</div>
            <h3 style={{ marginBottom: 8 }}>黄金三章生成</h3>
            <p style={{ fontSize: 13, color: "#888", marginBottom: 16 }}>
              AI 将基于你的创作上下文自动生成开篇三章。
            </p>
            {resumableSession && !resuming && (
              <div style={{
                textAlign: "left", padding: 16, background: "#e8f0fe",
                borderRadius: 6, marginBottom: 16, fontSize: 12,
              }}>
                <strong style={{ color: "#1967d2" }}>📌 检测到未完成的黄金三章生成</strong>
                <p style={{ margin: "8px 0"}}>
                  上次生成到第 {resumableSession.stage} 章，是否继续？
                </p>
                <div style={{ display: "flex", gap: 8 }}>
                  <button style={{ ...btnPrimary, background: "#1967d2" }}
                    onClick={handleResume} disabled={generating}>
                    ▶ 继续生成
                  </button>
                  <button style={btnSecondary}
                    onClick={() => setResumableSession(null)}>
                    忽略，重新开始
                  </button>
                </div>
              </div>
            )}
            {missing.length > 0 ? (
              <div style={{
                textAlign: "left", padding: 16, background: "#fef7e0",
                borderRadius: 6, marginBottom: 16, fontSize: 12,
              }}>
                <strong style={{ color: "#e37400" }}>⚠️ 前置条件不满足：</strong>
                <ul style={{ margin: "8px 0 0", paddingLeft: 20 }}>
                  {missing.map((m, i) => <li key={i}>{m}</li>)}
                </ul>
                <p style={{ marginTop: 8, color: "#888" }}>
                  请先完成「项目设置」，填写以上缺失项。
                </p>
              </div>
            ) : (
              <button style={{ ...btnSuccess, fontSize: 16, padding: "12px 32px" }}
                onClick={handleStart} disabled={generating}>
                {generating ? "⏳ 生成中..." : "🚀 开始生成"}
              </button>
            )}
          </div>
        )}

        {/* Step 1-3: 章节 */}
        {step >= 1 && step < 4 && (
          <div>
            {notes.length > 0 && (
              <div style={{
                padding: 8, background: "#fef7e0", borderRadius: 4,
                marginBottom: 12, fontSize: 12,
              }}>
                <strong style={{ color: "#e37400" }}>📋 一致性检查：</strong>
                {notes.map((n, i) => <div key={i} style={{ marginTop: 4 }}>• {n}</div>)}
              </div>
            )}

            {editing ? (
              <textarea style={{
                width: "100%", minHeight: 300, fontFamily: "monospace", fontSize: 13,
                border: "1px solid #d0d0d0", borderRadius: 4, padding: 8, resize: "vertical",
              }}
                value={editText || currentChapter}
                onChange={e => setEditText(e.target.value)}
              />
            ) : (
              <pre style={{
                whiteSpace: "pre-wrap", fontFamily: "Georgia, serif",
                fontSize: 14, lineHeight: 1.8, padding: 16,
                background: "#fafafa", borderRadius: 4, border: "1px solid #e0e0e0",
                maxHeight: "50vh", overflow: "auto",
              }}>
                {currentChapter}
              </pre>
            )}

            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              {step < 3 && (
                <button style={btnPrimary} onClick={handleContinue} disabled={generating}>
                  {generating ? "⏳ 生成中..." : "满意，继续 →"}
                </button>
              )}
              {step === 3 && (
                <button style={btnSuccess} onClick={handleFinalize} disabled={generating}>
                  {generating ? "⏳ 保存中..." : "✅ 完成！保存为章节"}
                </button>
              )}
              <button style={btnWarning} onClick={handleRegenerate} disabled={generating}>
                🔄 重新生成
              </button>
              {!editing ? (
                <button style={btnSecondary} onClick={() => { setEditing(true); setEditText(currentChapter); }}>
                  ✏️ 修改
                </button>
              ) : (
                <button style={btnSecondary} onClick={() => { setEditing(false); setEditText(""); }}>
                  👁️ 预览
                </button>
              )}
            </div>
          </div>
        )}

        {/* Step 4: 完成 */}
        {step === 4 && (
          <div style={{ textAlign: "center", padding: 40 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🎉</div>
            <h3>黄金三章已生成并保存！</h3>
            <p style={{ fontSize: 13, color: "#888", marginBottom: 16 }}>
              第1章、第2章、第3章 已添加到章节列表。
            </p>
            <button style={btnPrimary} onClick={onClose}>返回编辑器</button>
          </div>
        )}
      </div>
    </div>
  );
};
