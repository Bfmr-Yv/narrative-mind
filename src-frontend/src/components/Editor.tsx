/**
 * Monaco Editor 组件 — Narrative Mind v4.0
 *
 * Phase E: 编辑器底座 + Agent 标注层 + 内联建议。
 * Phase H: Glyph 黄点 + 建议弹窗 + accept/reject 文本替换。
 */

import { useRef, useEffect, useCallback, useState } from "react";
import MonacoEditor, { OnMount, OnChange } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import type { AgentAnnotation } from "../types";
import type { ProposalReady } from "../api/events";

interface EditorProps {
  /** 章节文本 */
  content: string;
  /** 文本变更回调 */
  onChange?: (value: string) => void;
  /** Agent 标注列表 */
  annotations?: AgentAnnotation[];
  /** 修改建议列表（带 suggestion 文本） */
  proposals?: ProposalReady[];
  /** 是否只读 */
  readOnly?: boolean;
}

/** 弹出面板的状态 */
interface PopupState {
  proposalId: string;
  title: string;
  agentName: string;
  severity: string;
  suggestion: string;
  range: { startLine: number; startCol: number; endLine: number; endCol: number };
  top: number;
  left: number;
}

const SEVERITY_COLORS: Record<string, string> = {
  Info: "#4285f4",
  Warn: "#fbbc04",
  Critical: "#ea4335",
};

export function Editor({
  content,
  onChange,
  annotations = [],
  proposals = [],
  readOnly = false,
}: EditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<any>(null);
  const decorationsRef = useRef<string[]>([]);
  const glyphRef = useRef<string[]>([]);
  const proposalsRef = useRef<ProposalReady[]>([]);
  const [popup, setPopup] = useState<PopupState | null>(null);

  // ── Sync proposals to ref (OnMount 闭包只执行一次，必须通过 ref 读最新值) ──
  useEffect(() => {
    proposalsRef.current = proposals;
  }, [proposals]);

  // ── Editor mount ──
  const handleMount: OnMount = useCallback(
    (editor, monaco) => {
      editorRef.current = editor;
      monacoRef.current = monaco;

      monaco.editor.defineTheme("narrative-mind", {
        base: "vs",
        inherit: true,
        rules: [
          { token: "comment", foreground: "999999", fontStyle: "italic" },
        ],
        colors: {
          "editor.background": "#fafafa",
          "editor.lineHighlightBackground": "#f0f4ff",
          "editorLineNumber.foreground": "#c0c0c0",
        },
      });
      monaco.editor.setTheme("narrative-mind");

      editor.updateOptions({
        fontSize: 16,
        lineHeight: 28,
        fontFamily: '"Noto Serif SC", "Source Han Serif SC", serif',
        wordWrap: "on",
        minimap: { enabled: false },
        lineNumbers: "on",
        renderLineHighlight: "line",
        scrollBeyondLastLine: false,
        padding: { top: 16, bottom: 16 },
        glyphMargin: true, // ← Phase H: 启用 glyph margin
        readOnly,
      });

      // ── Glyph click handler ──
      editor.onMouseDown((e) => {
        const target = e.target;
        if (!target.position) return;

        const { lineNumber } = target.position;
        // Find a proposal at the clicked line (read from ref — always latest)
        const match = proposalsRef.current.find(
          (p) =>
            p.location &&
            p.location.start_line <= lineNumber &&
            p.location.end_line >= lineNumber
        );
        if (!match || !match.location) return;

        // Compute popup position from editor coordinates
        const coords = editor.getScrolledVisiblePosition(target.position);
        if (!coords) return;
        const editorDom = editor.getDomNode();
        if (!editorDom) return;
        const rect = editorDom.getBoundingClientRect();

        setPopup({
          proposalId: match.proposal_id,
          title: match.title,
          agentName: match.agent_id,
          severity: match.severity,
          suggestion: match.suggestion,
          range: {
            startLine: match.location.start_line,
            startCol: match.location.start_column,
            endLine: match.location.end_line,
            endCol: match.location.end_column,
          },
          top: coords.top + 28 + rect.top,
          left: coords.left + rect.left + 60,
        });
      });
    },
    [readOnly]
  );

  // ── 标注层更新（背景高亮 + hover） ──
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;

    const model = editor.getModel();
    if (!model) return;

    const monaco = monacoRef.current;
    if (!monaco) return;

    const newDecorations: editor.IModelDeltaDecoration[] = annotations.map((ann) => {
      const startLine = ann.location?.start_line ?? 1;
      const startCol = ann.location?.start_column ?? 1;
      const endLine = ann.location?.end_line ?? startLine;
      const endCol = ann.location?.end_column ?? startCol + 10;

      const sevKey = ann.severity?.toLowerCase() ?? "info";
      const bgColor: Record<string, string> = {
        info: "rgba(66, 133, 244, 0.10)",
        warn: "rgba(251, 188, 4, 0.12)",
        critical: "rgba(234, 67, 53, 0.12)",
      };
      const borderColor: Record<string, string> = {
        info: "rgba(66, 133, 244, 0.5)",
        warn: "rgba(251, 188, 4, 0.5)",
        critical: "rgba(234, 67, 53, 0.5)",
      };

      return {
        range: new monaco.Range(startLine, startCol, endLine, endCol),
        options: {
          className: `agent-annotation agent-${sevKey}`,
          inlineClassName: `agent-inline-${sevKey}`,
          overviewRuler: {
            color: borderColor[sevKey] ?? borderColor.info,
            position: 1,
          },
          minimap: {
            color: borderColor[sevKey] ?? borderColor.info,
            position: 1,
          },
          hoverMessage: {
            value: `**${ann.agent_name}**: ${ann.message}`,
          },
        },
      };
    });

    decorationsRef.current = editor.deltaDecorations(
      decorationsRef.current,
      newDecorations
    );
  }, [annotations]);

  // ── 建议 Glyph 层 ──
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;

    const model = editor.getModel();
    if (!model) return;

    const monaco = monacoRef.current;
    if (!monaco) return;

    const newGlyphs: editor.IModelDeltaDecoration[] = proposals
      .filter((p) => p.location != null)
      .map((p) => {
        const loc = p.location!;
        const color = SEVERITY_COLORS[p.severity] ?? SEVERITY_COLORS.Info;

        return {
          range: new monaco.Range(
            loc.start_line,
            loc.start_column,
            loc.start_line,
            loc.start_column + 1
          ),
          options: {
            glyphMarginClassName: "proposal-glyph",
            glyphMarginHoverMessage: {
              value: `**${p.agent_id}**: ${p.title}\n\n${p.suggestion.substring(0, 200)}`,
            },
            glyphMargin: {
              position: 1,
            },
            // Use a custom CSS class to draw the dot
            before: {
              content: "",
              inlineClassName: "proposal-glyph-hidden",
            },
          },
        };
      });

    glyphRef.current = editor.deltaDecorations(glyphRef.current, newGlyphs);
  }, [proposals]);

  // ── Accept proposal → replace text ──
  const handleAccept = useCallback(() => {
    if (!popup || !editorRef.current) return;
    const ed = editorRef.current;
    const model = ed.getModel();
    if (!model) return;
    const monaco = monacoRef.current;
    if (!monaco) return;

    const { startLine, startCol, endLine, endCol } = popup.range;
    const range = new monaco.Range(startLine, startCol, endLine, endCol);

    ed.executeEdits("proposal-accept", [
      {
        range,
        text: popup.suggestion,
        forceMoveMarkers: true,
      },
    ]);

    // Notify parent of content change
    const newValue = model.getValue();
    onChange?.(newValue);

    setPopup(null);
  }, [popup, onChange]);

  // ── Reject proposal → dismiss popup ──
  const handleReject = useCallback(() => {
    setPopup(null);
  }, []);

  // ── Close popup on Escape ──
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPopup(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // ── Dismiss popup on scroll ──
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    const disp = editor.onDidScrollChange(() => {
      setPopup(null);
    });
    return () => disp.dispose();
  }, [popup /* re-register when popup changes (including null → open) */]);

  // ── Reposition popup on resize ──
  useEffect(() => {
    if (!popup || !editorRef.current) return;
    const editorDom = editorRef.current.getDomNode();
    if (!editorDom) return;

    const reposition = () => {
      if (!popup.range) return;
      const ed = editorRef.current;
      if (!ed) return;
      // Recompute position from the proposal's start location
      const pos = ed.getScrolledVisiblePosition({
        lineNumber: popup.range.startLine,
        column: popup.range.startCol,
      });
      if (!pos) return;
      const rect = editorDom.getBoundingClientRect();
      setPopup((prev) =>
        prev
          ? { ...prev, top: pos.top + 28 + rect.top, left: pos.left + rect.left + 60 }
          : null
      );
    };

    const observer = new ResizeObserver(() => reposition());
    observer.observe(editorDom);
    return () => observer.disconnect();
  }, [popup?.proposalId]); // re-run when popup content changes

  // ── Content sync ──
  const handleChange: OnChange = useCallback(
    (value) => {
      onChange?.(value ?? "");
    },
    [onChange]
  );

  return (
    <div
      className="editor-container"
      style={{ height: "100%", width: "100%", position: "relative" }}
    >
      <MonacoEditor
        language="plaintext"
        value={content}
        onChange={handleChange}
        onMount={handleMount}
        options={{
          readOnly,
          wordWrap: "on",
          glyphMargin: true,
        }}
      />

      {/* ── Proposal popup ── */}
      {popup && (
        <div
          className="proposal-popup"
          style={{
            position: "fixed",
            top: popup.top,
            left: popup.left,
            width: 360,
            maxHeight: 400,
            overflow: "auto",
            background: "#fff",
            border: "1px solid #e0e0e0",
            borderRadius: 8,
            boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
            zIndex: 9999,
            padding: 16,
            fontSize: 13,
          }}
        >
          {/* Header */}
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>{popup.title}</span>
            <span
              style={{
                background: SEVERITY_COLORS[popup.severity] ?? "#888",
                color: "#fff",
                padding: "2px 8px",
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 600,
              }}
            >
              {popup.severity}
            </span>
          </div>
          <div style={{ color: "#666", fontSize: 12, marginBottom: 8 }}>
            来自 {popup.agentName}
          </div>

          {/* Suggestion preview */}
          <div
            style={{
              background: "#f8f9fa",
              border: "1px solid #e8e8e8",
              borderRadius: 4,
              padding: 10,
              fontFamily: '"Noto Serif SC", serif',
              fontSize: 14,
              lineHeight: 1.6,
              maxHeight: 200,
              overflow: "auto",
              whiteSpace: "pre-wrap",
              marginBottom: 12,
            }}
          >
            {popup.suggestion}
          </div>

          {/* Action buttons */}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button
              onClick={handleReject}
              style={{
                padding: "6px 14px",
                border: "1px solid #ccc",
                borderRadius: 4,
                background: "#fff",
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              ✕ 忽略
            </button>
            <button
              onClick={handleAccept}
              style={{
                padding: "6px 14px",
                border: "none",
                borderRadius: 4,
                background: "#4285f4",
                color: "#fff",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              ✓ 应用建议
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
