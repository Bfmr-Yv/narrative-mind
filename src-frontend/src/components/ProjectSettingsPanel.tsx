/**
 * ProjectSettingsPanel — Phase B: 项目创作上下文设置
 *
 * 5 Tab 表单 + AI 辅助填写，对应 ProjectContext 的 5 个 section。
 */

import { useState, useEffect, useCallback, type FC } from "react";
import type {
  ProjectContext, WorldRules, CharacterProfile,
  PlotOutline, ChapterOutline, StyleGuide, ThemeMap, ThemeArc,
} from "../types";
import { expandContextSection } from "../api/analysis";

// ── Props ──

interface Props {
  projectId: string;
  projectContext: ProjectContext | null;
  onSave: (ctx: ProjectContext, expectedVersion?: number) => Promise<void>;
  onClose?: () => void;
}

type TabKey = "world_rules" | "character_profiles" | "plot_outline" | "style_guide" | "theme_map";

const TABS: { key: TabKey; label: string }[] = [
  { key: "world_rules", label: "世界观" },
  { key: "character_profiles", label: "角色" },
  { key: "plot_outline", label: "大纲" },
  { key: "style_guide", label: "风格" },
  { key: "theme_map", label: "主题" },
];

// ── 样式常量（复用 LibraryPanel 风格） ──

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "4px 6px", fontSize: 12,
  border: "1px solid #d0d0d0", borderRadius: 3, outline: "none",
};

const textareaStyle: React.CSSProperties = {
  ...inputStyle, minHeight: 60, resize: "vertical",
};

const btnPrimary: React.CSSProperties = {
  padding: "4px 12px", fontSize: 12, border: "none",
  borderRadius: 3, background: "#4285f4", color: "#fff", cursor: "pointer",
};

const btnSecondary: React.CSSProperties = {
  padding: "4px 12px", fontSize: 12, border: "1px solid #ccc",
  borderRadius: 3, background: "#fff", cursor: "pointer",
};

const btnSmall: React.CSSProperties = {
  padding: "3px 6px", fontSize: 11, border: "1px solid #d0d0d0",
  borderRadius: 3, background: "#fff", cursor: "pointer",
};

const btnDanger: React.CSSProperties = {
  ...btnSmall, color: "#e74c3c", borderColor: "#e74c3c",
};

const btnAi: React.CSSProperties = {
  ...btnSmall, background: "#f0f4ff", borderColor: "#4285f4", color: "#4285f4",
};

const labelStyle: React.CSSProperties = {
  fontSize: 11, color: "#888", marginBottom: 2, display: "block",
};

const sectionStyle: React.CSSProperties = {
  marginBottom: 10,
};

const tagStyle: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: 4,
  padding: "2px 6px", fontSize: 11, background: "#e8f0fe",
  borderRadius: 3, margin: "2px 4px 2px 0",
};

// ── 空模板 ──

function emptyWorldRules(): WorldRules {
  return { magic_system: "", technology_level: "", social_structure: "", geography: "", custom_rules: [] };
}

function emptyCharacterProfile(): CharacterProfile {
  return { character_id: crypto.randomUUID(), name: "", background: "", personality: "", goals: [], speech_patterns: "" };
}

function emptyPlotOutline(): PlotOutline {
  return { main_plot: "", subplots: [], foreshadow_plan: [], chapter_outlines: [] };
}

function emptyChapterOutline(idx: number): ChapterOutline {
  return { chapter_index: idx, summary: "", key_events: [] };
}

function emptyStyleGuide(): StyleGuide {
  return { prose_style: "", sentence_preferences: "", dialogue_conventions: "", narrative_distance: "" };
}

function emptyThemeMap(): ThemeMap {
  return { primary_themes: [], imagery_motifs: [], theme_arcs: [] };
}

function emptyThemeArc(): ThemeArc {
  return { theme: "", current_stage: "", planned_development: "" };
}

// ── 辅助 ──

function jsonOrEmpty(obj: unknown): string {
  try { return JSON.stringify(obj); } catch { return "{}"; }
}

// ── 组件 ──

export const ProjectSettingsPanel: FC<Props> = ({ projectId, projectContext, onSave, onClose }) => {
  const ctx = projectContext;
  const [tab, setTab] = useState<TabKey>("world_rules");
  const [saving, setSaving] = useState(false);
  const [expanding, setExpanding] = useState(false);

  // 本地编辑状态
  const [worldRules, setWorldRules] = useState<WorldRules>(ctx?.world_rules ?? emptyWorldRules());
  const [charProfiles, setCharProfiles] = useState<CharacterProfile[]>(ctx?.character_profiles ?? []);
  const [plotOutline, setPlotOutline] = useState<PlotOutline>(ctx?.plot_outline ?? emptyPlotOutline());
  const [styleGuide, setStyleGuide] = useState<StyleGuide>(ctx?.style_guide ?? emptyStyleGuide());
  const [themeMap, setThemeMap] = useState<ThemeMap>(ctx?.theme_map ?? emptyThemeMap());

  // Sync from props when context changes
  useEffect(() => {
    if (ctx) {
      setWorldRules(ctx.world_rules ?? emptyWorldRules());
      setCharProfiles(ctx.character_profiles ?? []);
      setPlotOutline(ctx.plot_outline ?? emptyPlotOutline());
      setStyleGuide(ctx.style_guide ?? emptyStyleGuide());
      setThemeMap(ctx.theme_map ?? emptyThemeMap());
    }
  }, [ctx?.context_version, ctx?.project_id]);

  // ── 保存 ──
  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const updated: ProjectContext = {
        project_id: projectId,
        context_version: ctx?.context_version ?? 1,
        updated_at: new Date().toISOString(),
        world_rules: worldRules.magic_system ? worldRules : null,
        character_profiles: charProfiles,
        plot_outline: plotOutline.main_plot ? plotOutline : null,
        style_guide: styleGuide.prose_style ? styleGuide : null,
        theme_map: themeMap.primary_themes.length > 0 ? themeMap : null,
      };
      await onSave(updated, ctx?.context_version);
    } finally {
      setSaving(false);
    }
  }, [projectId, ctx, worldRules, charProfiles, plotOutline, styleGuide, themeMap, onSave]);

  // ── AI 辅助填写 ──
  const handleAiExpand = useCallback(async () => {
    setExpanding(true);
    try {
      let currentJson: string;
      switch (tab) {
        case "world_rules": currentJson = jsonOrEmpty(worldRules); break;
        case "character_profiles": currentJson = jsonOrEmpty(charProfiles); break;
        case "plot_outline": currentJson = jsonOrEmpty(plotOutline); break;
        case "style_guide": currentJson = jsonOrEmpty(styleGuide); break;
        case "theme_map": currentJson = jsonOrEmpty(themeMap); break;
      }
      const result = await expandContextSection(tab, currentJson, projectId);
      try {
        const parsed = JSON.parse(result);
        switch (tab) {
          case "world_rules": setWorldRules(parsed as WorldRules); break;
          case "character_profiles": setCharProfiles(Array.isArray(parsed) ? parsed : [parsed]); break;
          case "plot_outline": setPlotOutline(parsed as PlotOutline); break;
          case "style_guide": setStyleGuide(parsed as StyleGuide); break;
          case "theme_map": setThemeMap(parsed as ThemeMap); break;
        }
      } catch {
        // LLM 输出无法解析为 JSON，忽略
        console.warn("AI expand result not valid JSON:", result.substring(0, 200));
      }
    } catch (e) {
      console.error("AI expand failed:", e);
    } finally {
      setExpanding(false);
    }
  }, [tab, projectId, worldRules, charProfiles, plotOutline, styleGuide, themeMap]);

  // ── 动态列表辅助 ──

  const addStringItem = (arr: string[], setArr: (v: string[]) => void) => {
    const val = prompt("输入新项：");
    if (val?.trim()) setArr([...arr, val.trim()]);
  };

  const removeStringItem = (arr: string[], idx: number, setArr: (v: string[]) => void) => {
    setArr(arr.filter((_, i) => i !== idx));
  };

  // ── Tab 内容 ──

  const renderTab = () => {
    switch (tab) {
      // ─── 世界观 ───
      case "world_rules": return (
        <div>
          <div style={sectionStyle}>
            <label style={labelStyle}>力量体系</label>
            <textarea style={textareaStyle} value={worldRules.magic_system}
              onChange={e => setWorldRules({ ...worldRules, magic_system: e.target.value })} />
          </div>
          <div style={sectionStyle}>
            <label style={labelStyle}>科技水平</label>
            <input style={inputStyle} value={worldRules.technology_level}
              onChange={e => setWorldRules({ ...worldRules, technology_level: e.target.value })} />
          </div>
          <div style={sectionStyle}>
            <label style={labelStyle}>社会结构</label>
            <input style={inputStyle} value={worldRules.social_structure}
              onChange={e => setWorldRules({ ...worldRules, social_structure: e.target.value })} />
          </div>
          <div style={sectionStyle}>
            <label style={labelStyle}>地理环境</label>
            <textarea style={textareaStyle} value={worldRules.geography}
              onChange={e => setWorldRules({ ...worldRules, geography: e.target.value })} />
          </div>
          <div style={sectionStyle}>
            <label style={labelStyle}>自定义规则</label>
            {worldRules.custom_rules.map((r, i) => (
              <div key={i} style={{ display: "flex", gap: 4, marginBottom: 4 }}>
                <input style={inputStyle} value={r}
                  onChange={e => {
                    const next = [...worldRules.custom_rules];
                    next[i] = e.target.value;
                    setWorldRules({ ...worldRules, custom_rules: next });
                  }} />
                <button style={btnDanger} onClick={() => removeStringItem(worldRules.custom_rules, i, (v) => setWorldRules({ ...worldRules, custom_rules: v }))}>
                  ✕
                </button>
              </div>
            ))}
            <button style={btnSmall} onClick={() => setWorldRules({ ...worldRules, custom_rules: [...worldRules.custom_rules, ""] })}>
              + 添加规则
            </button>
          </div>
        </div>
      );

      // ─── 角色 ───
      case "character_profiles": return (
        <div>
          {charProfiles.map((cp, i) => (
            <details key={i} style={{ ...sectionStyle, border: "1px solid #e0e0e0", borderRadius: 4, padding: 8 }}>
              <summary style={{ fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
                {cp.name || `角色 ${i + 1}`}
                <button style={{ ...btnDanger, marginLeft: 8, fontSize: 10 }} onClick={e => {
                  e.preventDefault();
                  setCharProfiles(charProfiles.filter((_, j) => j !== i));
                }}>删除</button>
              </summary>
              <div style={{ marginTop: 8 }}>
                <label style={labelStyle}>名称</label>
                <input style={inputStyle} value={cp.name}
                  onChange={e => { const n = [...charProfiles]; n[i] = { ...n[i], name: e.target.value }; setCharProfiles(n); }} />
                <label style={labelStyle}>背景</label>
                <textarea style={textareaStyle} value={cp.background}
                  onChange={e => { const n = [...charProfiles]; n[i] = { ...n[i], background: e.target.value }; setCharProfiles(n); }} />
                <label style={labelStyle}>性格</label>
                <input style={inputStyle} value={cp.personality}
                  onChange={e => { const n = [...charProfiles]; n[i] = { ...n[i], personality: e.target.value }; setCharProfiles(n); }} />
                <label style={labelStyle}>目标（逗号分隔）</label>
                <input style={inputStyle} value={cp.goals.join(", ")}
                  onChange={e => { const n = [...charProfiles]; n[i] = { ...n[i], goals: e.target.value.split(",").map(s => s.trim()).filter(Boolean) }; setCharProfiles(n); }} />
                <label style={labelStyle}>语言特点</label>
                <input style={inputStyle} value={cp.speech_patterns}
                  onChange={e => { const n = [...charProfiles]; n[i] = { ...n[i], speech_patterns: e.target.value }; setCharProfiles(n); }} />
              </div>
            </details>
          ))}
          <button style={btnSmall} onClick={() => setCharProfiles([...charProfiles, emptyCharacterProfile()])}>
            + 添加角色
          </button>
        </div>
      );

      // ─── 大纲 ───
      case "plot_outline": return (
        <div>
          <div style={sectionStyle}>
            <label style={labelStyle}>主线情节</label>
            <textarea style={{ ...textareaStyle, minHeight: 80 }} value={plotOutline.main_plot}
              onChange={e => setPlotOutline({ ...plotOutline, main_plot: e.target.value })} />
          </div>
          <div style={sectionStyle}>
            <label style={labelStyle}>支线故事</label>
            {plotOutline.subplots.map((s, i) => (
              <div key={i} style={{ display: "flex", gap: 4, marginBottom: 4 }}>
                <input style={inputStyle} value={s}
                  onChange={e => { const n = [...plotOutline.subplots]; n[i] = e.target.value; setPlotOutline({ ...plotOutline, subplots: n }); }} />
                <button style={btnDanger} onClick={() => removeStringItem(plotOutline.subplots, i, (v) => setPlotOutline({ ...plotOutline, subplots: v }))}>✕</button>
              </div>
            ))}
            <button style={btnSmall} onClick={() => setPlotOutline({ ...plotOutline, subplots: [...plotOutline.subplots, ""] })}>+ 添加支线</button>
          </div>
          <div style={sectionStyle}>
            <label style={labelStyle}>伏笔线索</label>
            {plotOutline.foreshadow_plan.map((f, i) => (
              <div key={i} style={{ display: "flex", gap: 4, marginBottom: 4 }}>
                <input style={inputStyle} value={f}
                  onChange={e => { const n = [...plotOutline.foreshadow_plan]; n[i] = e.target.value; setPlotOutline({ ...plotOutline, foreshadow_plan: n }); }} />
                <button style={btnDanger} onClick={() => removeStringItem(plotOutline.foreshadow_plan, i, (v) => setPlotOutline({ ...plotOutline, foreshadow_plan: v }))}>✕</button>
              </div>
            ))}
            <button style={btnSmall} onClick={() => setPlotOutline({ ...plotOutline, foreshadow_plan: [...plotOutline.foreshadow_plan, ""] })}>+ 添加伏笔</button>
          </div>
          <div style={sectionStyle}>
            <label style={labelStyle}>章节大纲</label>
            {plotOutline.chapter_outlines.map((co, i) => (
              <details key={i} style={{ border: "1px solid #e0e0e0", borderRadius: 4, padding: 6, marginBottom: 4 }}>
                <summary style={{ fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
                  第{co.chapter_index}章: {co.summary.substring(0, 30) || "（空）"}
                  <button style={{ ...btnDanger, marginLeft: 8, fontSize: 10 }} onClick={e => {
                    e.preventDefault();
                    setPlotOutline({ ...plotOutline, chapter_outlines: plotOutline.chapter_outlines.filter((_, j) => j !== i) });
                  }}>删除</button>
                </summary>
                <div style={{ marginTop: 6 }}>
                  <label style={labelStyle}>章节序号</label>
                  <input type="number" style={inputStyle} value={co.chapter_index}
                    onChange={e => { const n = [...plotOutline.chapter_outlines]; n[i] = { ...n[i], chapter_index: parseInt(e.target.value) || 0 }; setPlotOutline({ ...plotOutline, chapter_outlines: n }); }} />
                  <label style={labelStyle}>摘要</label>
                  <input style={inputStyle} value={co.summary}
                    onChange={e => { const n = [...plotOutline.chapter_outlines]; n[i] = { ...n[i], summary: e.target.value }; setPlotOutline({ ...plotOutline, chapter_outlines: n }); }} />
                  <label style={labelStyle}>关键事件（逗号分隔）</label>
                  <input style={inputStyle} value={co.key_events.join(", ")}
                    onChange={e => { const n = [...plotOutline.chapter_outlines]; n[i] = { ...n[i], key_events: e.target.value.split(",").map(s => s.trim()).filter(Boolean) }; setPlotOutline({ ...plotOutline, chapter_outlines: n }); }} />
                </div>
              </details>
            ))}
            <button style={btnSmall} onClick={() => setPlotOutline({
              ...plotOutline,
              chapter_outlines: [...plotOutline.chapter_outlines, emptyChapterOutline(plotOutline.chapter_outlines.length + 1)]
            })}>+ 添加章节</button>
          </div>
        </div>
      );

      // ─── 风格 ───
      case "style_guide": return (
        <div>
          <div style={sectionStyle}>
            <label style={labelStyle}>文体风格</label>
            <textarea style={textareaStyle} value={styleGuide.prose_style}
              onChange={e => setStyleGuide({ ...styleGuide, prose_style: e.target.value })} />
          </div>
          <div style={sectionStyle}>
            <label style={labelStyle}>句式偏好</label>
            <textarea style={textareaStyle} value={styleGuide.sentence_preferences}
              onChange={e => setStyleGuide({ ...styleGuide, sentence_preferences: e.target.value })} />
          </div>
          <div style={sectionStyle}>
            <label style={labelStyle}>对话惯例</label>
            <textarea style={textareaStyle} value={styleGuide.dialogue_conventions}
              onChange={e => setStyleGuide({ ...styleGuide, dialogue_conventions: e.target.value })} />
          </div>
          <div style={sectionStyle}>
            <label style={labelStyle}>叙事距离</label>
            <input style={inputStyle} value={styleGuide.narrative_distance}
              onChange={e => setStyleGuide({ ...styleGuide, narrative_distance: e.target.value })} />
          </div>
        </div>
      );

      // ─── 主题 ───
      case "theme_map": return (
        <div>
          <div style={sectionStyle}>
            <label style={labelStyle}>主要主题（标签）</label>
            <div style={{ display: "flex", flexWrap: "wrap" }}>
              {themeMap.primary_themes.map((t, i) => (
                <span key={i} style={tagStyle}>
                  {t}
                  <span style={{ cursor: "pointer", color: "#e74c3c" }}
                    onClick={() => removeStringItem(themeMap.primary_themes, i, (v) => setThemeMap({ ...themeMap, primary_themes: v }))}>✕</span>
                </span>
              ))}
            </div>
            <button style={btnSmall} onClick={() => addStringItem(themeMap.primary_themes, (v) => setThemeMap({ ...themeMap, primary_themes: v }))}>
              + 添加主题
            </button>
          </div>
          <div style={sectionStyle}>
            <label style={labelStyle}>意象母题（标签）</label>
            <div style={{ display: "flex", flexWrap: "wrap" }}>
              {themeMap.imagery_motifs.map((m, i) => (
                <span key={i} style={tagStyle}>
                  {m}
                  <span style={{ cursor: "pointer", color: "#e74c3c" }}
                    onClick={() => removeStringItem(themeMap.imagery_motifs, i, (v) => setThemeMap({ ...themeMap, imagery_motifs: v }))}>✕</span>
                </span>
              ))}
            </div>
            <button style={btnSmall} onClick={() => addStringItem(themeMap.imagery_motifs, (v) => setThemeMap({ ...themeMap, imagery_motifs: v }))}>
              + 添加母题
            </button>
          </div>
          <div style={sectionStyle}>
            <label style={labelStyle}>主题弧</label>
            {themeMap.theme_arcs.map((ta, i) => (
              <details key={i} style={{ border: "1px solid #e0e0e0", borderRadius: 4, padding: 6, marginBottom: 4 }}>
                <summary style={{ fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
                  {ta.theme || `主题弧 ${i + 1}`}
                  <button style={{ ...btnDanger, marginLeft: 8, fontSize: 10 }} onClick={e => {
                    e.preventDefault();
                    setThemeMap({ ...themeMap, theme_arcs: themeMap.theme_arcs.filter((_, j) => j !== i) });
                  }}>删除</button>
                </summary>
                <div style={{ marginTop: 6 }}>
                  <label style={labelStyle}>主题</label>
                  <input style={inputStyle} value={ta.theme}
                    onChange={e => { const n = [...themeMap.theme_arcs]; n[i] = { ...n[i], theme: e.target.value }; setThemeMap({ ...themeMap, theme_arcs: n }); }} />
                  <label style={labelStyle}>当前阶段</label>
                  <input style={inputStyle} value={ta.current_stage}
                    onChange={e => { const n = [...themeMap.theme_arcs]; n[i] = { ...n[i], current_stage: e.target.value }; setThemeMap({ ...themeMap, theme_arcs: n }); }} />
                  <label style={labelStyle}>发展规划</label>
                  <textarea style={textareaStyle} value={ta.planned_development}
                    onChange={e => { const n = [...themeMap.theme_arcs]; n[i] = { ...n[i], planned_development: e.target.value }; setThemeMap({ ...themeMap, theme_arcs: n }); }} />
                </div>
              </details>
            ))}
            <button style={btnSmall} onClick={() => setThemeMap({ ...themeMap, theme_arcs: [...themeMap.theme_arcs, emptyThemeArc()] })}>
              + 添加主题弧
            </button>
          </div>
        </div>
      );
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "#fff" }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 12px",
        borderBottom: "1px solid #e0e0e0",
      }}>
        <span style={{ fontSize: 14, fontWeight: 700 }}>📝 项目设置</span>
        <span style={{ flex: 1 }} />
        <button style={btnSecondary} onClick={handleSave} disabled={saving}>
          {saving ? "保存中..." : "💾 保存"}
        </button>
        {onClose && (
          <button style={btnSecondary} onClick={onClose}>✕ 关闭</button>
        )}
      </div>

      {/* Tabs */}
      <div style={{
        display: "flex", gap: 0, borderBottom: "1px solid #e0e0e0",
        padding: "0 12px", background: "#fafafa",
      }}>
        {TABS.map(t => (
          <button key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              padding: "6px 14px", fontSize: 12, border: "none",
              borderBottom: tab === t.key ? "2px solid #4285f4" : "2px solid transparent",
              background: "transparent", cursor: "pointer",
              color: tab === t.key ? "#4285f4" : "#666",
              fontWeight: tab === t.key ? 600 : 400,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div style={{ flex: 1, overflow: "auto", padding: "12px" }}>
        {renderTab()}
      </div>

      {/* Footer: AI Button + Save */}
      <div style={{
        display: "flex", gap: 8, padding: "8px 12px",
        borderTop: "1px solid #e0e0e0", background: "#fafafa",
      }}>
        <button style={btnAi} onClick={handleAiExpand} disabled={expanding}>
          {expanding ? "⏳ AI 思考中..." : "✨ AI 辅助填写"}
        </button>
        <span style={{ flex: 1 }} />
        <button style={btnPrimary} onClick={handleSave} disabled={saving}>
          {saving ? "保存中..." : "💾 保存"}
        </button>
      </div>
    </div>
  );
};
