/**
 * Monaco Editor 组件 — Narrative Mind v4.0
 *
 * Phase E: 编辑器底座 + Agent 标注层 + 内联建议。
 */

import { useRef, useEffect, useCallback } from "react";
import MonacoEditor, { OnMount, OnChange } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import type { AgentAnnotation } from "../types";

interface EditorProps {
  /** 章节文本 */
  content: string;
  /** 文本变更回调 */
  onChange?: (value: string) => void;
  /** Agent 标注列表 */
  annotations?: AgentAnnotation[];
  /** 是否只读 */
  readOnly?: boolean;
}

/**
 * 编辑器组件。
 *
 * 功能：
 * 1. Monaco Editor 底座（中文优化）
 * 2. Agent 标注层（Decoration）
 * 3. 内联建议 Widget
 */
export function Editor({ content, onChange, annotations = [], readOnly = false }: EditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const decorationsRef = useRef<string[]>([]);

  // ── Editor mount ──
  const handleMount: OnMount = useCallback((editor, monaco) => {
    editorRef.current = editor;

    // 中文优化配置
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

    // 字体配置
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
      readOnly,
    });
  }, [readOnly]);

  // ── 标注层更新 ──
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;

    const model = editor.getModel();
    if (!model) return;

    const newDecorations: editor.IModelDeltaDecoration[] = annotations.map((ann) => {
      const startLine = ann.location?.start_line ?? 1;
      const startCol = ann.location?.start_column ?? 1;
      const endLine = ann.location?.end_line ?? startLine;
      const endCol = ann.location?.end_column ?? startCol + 10;

      const severityColor = {
        info: "rgba(66, 133, 244, 0.15)",
        warn: "rgba(251, 188, 4, 0.15)",
        critical: "rgba(234, 67, 53, 0.15)",
      };

      const borderColor = {
        info: "rgba(66, 133, 244, 0.6)",
        warn: "rgba(251, 188, 4, 0.6)",
        critical: "rgba(234, 67, 53, 0.6)",
      };

      const severity = ann.severity?.toLowerCase() ?? "info";

      return {
        range: new (window as any).monaco.Range(startLine, startCol, endLine, endCol),
        options: {
          className: `agent-annotation agent-${severity}`,
          overviewRuler: {
            color: borderColor[severity as keyof typeof borderColor] ?? borderColor.info,
            position: 1, // Right
          },
          minimap: {
            color: borderColor[severity as keyof typeof borderColor] ?? borderColor.info,
            position: 1,
          },
          hoverMessage: {
            value: `**${ann.agent_name}**: ${ann.message}`,
          },
          after: {
            content: `  💬 ${ann.agent_name}`,
            color: "#888",
            fontStyle: "italic",
          },
        },
      };
    });

    decorationsRef.current = editor.deltaDecorations(
      decorationsRef.current,
      newDecorations
    );
  }, [annotations]);

  // ── Content sync ──
  const handleChange: OnChange = useCallback(
    (value) => {
      onChange?.(value ?? "");
    },
    [onChange]
  );

  return (
    <div className="editor-container" style={{ height: "100%", width: "100%" }}>
      <MonacoEditor
        language="plaintext"
        value={content}
        onChange={handleChange}
        onMount={handleMount}
        options={{
          readOnly,
          wordWrap: "on",
        }}
      />
    </div>
  );
}
