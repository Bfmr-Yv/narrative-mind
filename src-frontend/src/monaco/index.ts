/**
 * Monaco 编辑器配置入口
 *
 * Phase A 骨架：导出占位配置。
 * Phase E 完整实现：Monaco 初始化、主题配置、装饰系统注册。
 */

export const MONACO_EDITOR_OPTIONS = {
  language: "plaintext",
  theme: "vs-dark",
  fontSize: 16,
  lineHeight: 24,
  fontFamily:
    "'Cascadia Code', 'Fira Code', 'Source Han Serif SC', 'Noto Serif CJK SC', serif",
  minimap: { enabled: true },
  wordWrap: "on" as const,
  scrollBeyondLastLine: false,
  automaticLayout: true,
};

export function initMonaco(): void {
  // Phase E: 注册 Monaco 语言服务、自定义 token provider、装饰系统
  console.log("[Monaco] Phase A stub — editor integration deferred to Phase E");
}
