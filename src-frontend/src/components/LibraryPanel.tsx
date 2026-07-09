/**
 * LibraryPanel — Phase L2: 创作库面板
 *
 * 折叠面板，包含人物/地点/设定/伏笔四个标签，支持查看和编辑。
 */

import { useState, useEffect, useCallback, type FC } from "react";
import { useAppStore } from "../store";
import type { Character, Location, ForeshadowEntry } from "../types";

// ── 类型 ──

type TabKey = "character" | "location" | "setting" | "foreshadow";

// ── 角色状态指示 ──

const STATUS_DOT: Record<string, string> = {
  Alive: "●",
  Dead: "⚫",
  Unknown: "○",
};

// ── 空实体模板 ──

function emptyCharacter(projectId: string): Character {
  const ts = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    project_id: projectId,
    name: "",
    aliases: [],
    status: "Alive",
    current_location: null,
    role: "",
    summary: "",
    first_appearance_chapter: null,
    source: "manual",
    created_at: ts,
    updated_at: ts,
  };
}

function emptyLocation(projectId: string): Location {
  const ts = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    project_id: projectId,
    name: "",
    aliases: [],
    location_type: "",
    parent_location: null,
    description: "",
    features: [],
    created_at: ts,
    updated_at: ts,
  };
}

function emptyForeshadow(projectId: string): ForeshadowEntry {
  const ts = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    project_id: projectId,
    title: "",
    description: "",
    quote: null,
    setup_chapter_id: "",
    payoff_chapter_id: null,
    status: "Planted",
    related_characters: [],
    related_locations: [],
    created_at: ts,
    updated_at: ts,
  };
}

// ── 组件 ──

interface Props {
  projectId: string;
}

export const LibraryPanel: FC<Props> = ({ projectId }) => {
  // ── Zustand store ──
  const characters = useAppStore((s) => s.characters);
  const locations = useAppStore((s) => s.locations);
  const foreshadows = useAppStore((s) => s.foreshadows);
  const settings = useAppStore((s) => s.settings);
  const selectedEntity = useAppStore((s) => s.selectedEntity);
  const editingEntity = useAppStore((s) => s.editingEntity);
  const loadCharacters = useAppStore((s) => s.loadCharacters);
  const loadLocations = useAppStore((s) => s.loadLocations);
  const loadForeshadows = useAppStore((s) => s.loadForeshadows);
  const loadSettings = useAppStore((s) => s.loadSettings);
  const createCharacter = useAppStore((s) => s.createCharacter);
  const updateCharacter = useAppStore((s) => s.updateCharacter);
  const deleteCharacter = useAppStore((s) => s.deleteCharacter);
  const createLocation = useAppStore((s) => s.createLocation);
  const updateLocation = useAppStore((s) => s.updateLocation);
  const deleteLocation = useAppStore((s) => s.deleteLocation);
  const createForeshadow = useAppStore((s) => s.createForeshadow);
  const updateForeshadow = useAppStore((s) => s.updateForeshadow);
  const deleteForeshadow = useAppStore((s) => s.deleteForeshadow);
  const setProjectSetting = useAppStore((s) => s.setProjectSetting);
  const deleteProjectSetting = useAppStore((s) => s.deleteProjectSetting);
  const selectEntity = useAppStore((s) => s.selectEntity);
  const setEditing = useAppStore((s) => s.setEditing);
  const clearSelection = useAppStore((s) => s.clearSelection);

  // ── 本地状态 ──
  const [collapsed, setCollapsed] = useState(true);
  const [tab, setTab] = useState<TabKey>("character");

  // 编辑表单
  const [editChar, setEditChar] = useState<Character | null>(null);
  const [editLoc, setEditLoc] = useState<Location | null>(null);
  const [editFore, setEditFore] = useState<ForeshadowEntry | null>(null);
  const [editSettingKey, setEditSettingKey] = useState("");
  const [editSettingValue, setEditSettingValue] = useState("");

  // ── 展开时加载数据 ──
  useEffect(() => {
    if (!collapsed && projectId) {
      loadCharacters();
      loadLocations();
      loadForeshadows();
      loadSettings();
    }
  }, [collapsed, projectId]);

  // ── 添加 ──
  const handleAdd = useCallback(() => {
    switch (tab) {
      case "character": {
        const c = emptyCharacter(projectId);
        setEditChar(c);
        setEditing(true);
        break;
      }
      case "location": {
        const l = emptyLocation(projectId);
        setEditLoc(l);
        setEditing(true);
        break;
      }
      case "foreshadow": {
        const f = emptyForeshadow(projectId);
        setEditFore(f);
        setEditing(true);
        break;
      }
      case "setting": {
        setEditSettingKey("");
        setEditSettingValue("");
        setEditing(true);
        break;
      }
    }
  }, [tab, projectId, setEditing]);

  // ── 编辑已有 ──
  const handleEdit = useCallback(() => {
    if (!selectedEntity) return;
    switch (selectedEntity.type) {
      case "character": {
        const c = characters.find((ch) => ch.id === selectedEntity.id);
        if (c) { setEditChar({ ...c }); setEditing(true); }
        break;
      }
      case "location": {
        const l = locations.find((loc) => loc.id === selectedEntity.id);
        if (l) { setEditLoc({ ...l }); setEditing(true); }
        break;
      }
      case "foreshadow": {
        const f = foreshadows.find((fs) => fs.id === selectedEntity.id);
        if (f) { setEditFore({ ...f }); setEditing(true); }
        break;
      }
      case "setting": {
        const s = settings.find(([k]) => k === selectedEntity.id);
        if (s) { setEditSettingKey(s[0]); setEditSettingValue(s[1]); setEditing(true); }
        break;
      }
    }
  }, [selectedEntity, characters, locations, foreshadows, settings, setEditing]);

  // ── 保存 ──
  const handleSave = useCallback(async () => {
    if (editChar) {
      const c = { ...editChar, updated_at: new Date().toISOString() };
      if (characters.find((ch) => ch.id === c.id)) {
        await updateCharacter(c);
      } else {
        await createCharacter(c);
      }
      setEditChar(null);
    } else if (editLoc) {
      const l = { ...editLoc, updated_at: new Date().toISOString() };
      if (locations.find((loc) => loc.id === l.id)) {
        await updateLocation(l);
      } else {
        await createLocation(l);
      }
      setEditLoc(null);
    } else if (editFore) {
      const f = { ...editFore, updated_at: new Date().toISOString() };
      if (foreshadows.find((fs) => fs.id === f.id)) {
        await updateForeshadow(f);
      } else {
        await createForeshadow(f);
      }
      setEditFore(null);
    } else if (editSettingKey) {
      await setProjectSetting(editSettingKey, editSettingValue);
      setEditSettingKey("");
      setEditSettingValue("");
    }
    setEditing(false);
  }, [editChar, editLoc, editFore, editSettingKey, editSettingValue]);

  // ── 删除 ──
  const handleDelete = useCallback(async () => {
    if (!selectedEntity) return;
    switch (selectedEntity.type) {
      case "character":
        await deleteCharacter(selectedEntity.id);
        break;
      case "location":
        await deleteLocation(selectedEntity.id);
        break;
      case "foreshadow":
        await deleteForeshadow(selectedEntity.id);
        break;
      case "setting":
        await deleteProjectSetting(selectedEntity.id);
        break;
    }
    clearSelection();
  }, [selectedEntity]);

  // ── 角色列表行 ──
  const renderCharacterRow = (c: Character) => (
    <div
      key={c.id}
      onClick={() => selectEntity("character", c.id)}
      style={{
        padding: "4px 8px",
        cursor: "pointer",
        borderRadius: 3,
        background: selectedEntity?.id === c.id ? "#e8f0fe" : "transparent",
        fontSize: 12,
        marginBottom: 1,
      }}
    >
      <span style={{ marginRight: 4 }}>{STATUS_DOT[c.status] ?? "●"}</span>
      {c.name || "(未命名)"}
      <span style={{ color: "#999", fontSize: 11 }}>
        {" "}{c.role}{c.status !== "Alive" ? `·${c.status}` : ""}
        {c.current_location ? `·${c.current_location}` : ""}
      </span>
    </div>
  );

  // ── 地点列表行 ──
  const renderLocationRow = (l: Location) => (
    <div
      key={l.id}
      onClick={() => selectEntity("location", l.id)}
      style={{
        padding: "4px 8px",
        cursor: "pointer",
        borderRadius: 3,
        background: selectedEntity?.id === l.id ? "#e8f0fe" : "transparent",
        fontSize: 12,
        marginBottom: 1,
      }}
    >
      📍 {l.name || "(未命名)"}
      <span style={{ color: "#999", fontSize: 11 }}>
        {" "}{l.location_type}{l.parent_location ? `·${l.parent_location}` : ""}
      </span>
    </div>
  );

  // ── 设定列表行 ──
  const renderSettingRow = ([key, value]: [string, string]) => (
    <div
      key={key}
      onClick={() => selectEntity("setting", key)}
      style={{
        padding: "4px 8px",
        cursor: "pointer",
        borderRadius: 3,
        background: selectedEntity?.id === key ? "#e8f0fe" : "transparent",
        fontSize: 12,
        marginBottom: 1,
      }}
    >
      📋 <b>{key}</b>: {value.length > 40 ? value.slice(0, 40) + "…" : value}
    </div>
  );

  // ── 伏笔列表行 ──
  const renderForeshadowRow = (f: ForeshadowEntry) => {
    const resolved = f.status === "Resolved";
    return (
      <div
        key={f.id}
        onClick={() => selectEntity("foreshadow", f.id)}
        style={{
          padding: "4px 8px",
          cursor: "pointer",
          borderRadius: 3,
          background: selectedEntity?.id === f.id ? "#e8f0fe" : "transparent",
          fontSize: 12,
          marginBottom: 1,
        }}
      >
        🔮 {f.title || "(未命名)"}
        <span style={{ color: resolved ? "#34a853" : "#f9a825", fontSize: 11 }}>
          {" "}{resolved ? "✅已回收" : "⚠️未回收"}
        </span>
        <span style={{ color: "#999", fontSize: 11 }}>
          {" "}·第{f.setup_chapter_id || "?"}章
        </span>
      </div>
    );
  };

  // ── 内联编辑面板 ──
  const renderEditPanel = () => {
    if (!editingEntity) return null;

    // 编辑角色
    if (editChar) {
      return (
        <div style={{ padding: "8px 0", borderBottom: "1px solid #e0e0e0" }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>
            编辑: {editChar.name || "(新建角色)"}
          </div>
          <Row label="名字">
            <input style={inputStyle} value={editChar.name} onChange={(e) => setEditChar({ ...editChar, name: e.target.value })} />
          </Row>
          <Row label="身份">
            <input style={inputStyle} value={editChar.role} onChange={(e) => setEditChar({ ...editChar, role: e.target.value })} />
          </Row>
          <Row label="状态">
            <select style={inputStyle} value={editChar.status} onChange={(e) => setEditChar({ ...editChar, status: e.target.value as Character["status"] })}>
              <option value="Alive">● 存活</option>
              <option value="Dead">⚫ 已故</option>
              <option value="Unknown">○ 未知</option>
            </select>
          </Row>
          <Row label="位置">
            <input style={inputStyle} value={editChar.current_location ?? ""} onChange={(e) => setEditChar({ ...editChar, current_location: e.target.value || null })} />
          </Row>
          <Row label="摘要">
            <textarea style={{ ...inputStyle, height: 60, resize: "vertical" }} value={editChar.summary} onChange={(e) => setEditChar({ ...editChar, summary: e.target.value })} />
          </Row>
          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", marginTop: 8 }}>
            <button style={btnSecondary} onClick={() => { setEditChar(null); setEditing(false); }}>取消</button>
            <button style={btnPrimary} onClick={handleSave}>保存</button>
          </div>
        </div>
      );
    }

    // 编辑地点
    if (editLoc) {
      return (
        <div style={{ padding: "8px 0", borderBottom: "1px solid #e0e0e0" }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>
            编辑: {editLoc.name || "(新建地点)"}
          </div>
          <Row label="名称">
            <input style={inputStyle} value={editLoc.name} onChange={(e) => setEditLoc({ ...editLoc, name: e.target.value })} />
          </Row>
          <Row label="类型">
            <input style={inputStyle} value={editLoc.location_type} onChange={(e) => setEditLoc({ ...editLoc, location_type: e.target.value })} />
          </Row>
          <Row label="父地点">
            <input style={inputStyle} value={editLoc.parent_location ?? ""} onChange={(e) => setEditLoc({ ...editLoc, parent_location: e.target.value || null })} />
          </Row>
          <Row label="描述">
            <textarea style={{ ...inputStyle, height: 60, resize: "vertical" }} value={editLoc.description} onChange={(e) => setEditLoc({ ...editLoc, description: e.target.value })} />
          </Row>
          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", marginTop: 8 }}>
            <button style={btnSecondary} onClick={() => { setEditLoc(null); setEditing(false); }}>取消</button>
            <button style={btnPrimary} onClick={handleSave}>保存</button>
          </div>
        </div>
      );
    }

    // 编辑伏笔
    if (editFore) {
      return (
        <div style={{ padding: "8px 0", borderBottom: "1px solid #e0e0e0" }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>
            编辑: {editFore.title || "(新建伏笔)"}
          </div>
          <Row label="标题">
            <input style={inputStyle} value={editFore.title} onChange={(e) => setEditFore({ ...editFore, title: e.target.value })} />
          </Row>
          <Row label="描述">
            <textarea style={{ ...inputStyle, height: 60, resize: "vertical" }} value={editFore.description} onChange={(e) => setEditFore({ ...editFore, description: e.target.value })} />
          </Row>
          <Row label="状态">
            <select style={inputStyle} value={editFore.status} onChange={(e) => setEditFore({ ...editFore, status: e.target.value as ForeshadowEntry["status"] })}>
              <option value="Planted">埋下</option>
              <option value="Hinted">暗示</option>
              <option value="PayingOff">回收中</option>
              <option value="Resolved">已回收</option>
            </select>
          </Row>
          <Row label="埋设章节">
            <input style={inputStyle} value={editFore.setup_chapter_id} onChange={(e) => setEditFore({ ...editFore, setup_chapter_id: e.target.value })} />
          </Row>
          <Row label="回收章节">
            <input style={inputStyle} value={editFore.payoff_chapter_id ?? ""} onChange={(e) => setEditFore({ ...editFore, payoff_chapter_id: e.target.value || null })} />
          </Row>
          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", marginTop: 8 }}>
            <button style={btnSecondary} onClick={() => { setEditFore(null); setEditing(false); }}>取消</button>
            <button style={btnPrimary} onClick={handleSave}>保存</button>
          </div>
        </div>
      );
    }

    // 编辑设定 (key-value)
    if (editSettingKey !== undefined) {
      return (
        <div style={{ padding: "8px 0", borderBottom: "1px solid #e0e0e0" }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>编辑设定</div>
          <Row label="Key">
            <input style={inputStyle} value={editSettingKey} onChange={(e) => setEditSettingKey(e.target.value)} placeholder="例如: worldview" />
          </Row>
          <Row label="Value">
            <textarea style={{ ...inputStyle, height: 60, resize: "vertical" }} value={editSettingValue} onChange={(e) => setEditSettingValue(e.target.value)} />
          </Row>
          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", marginTop: 8 }}>
            <button style={btnSecondary} onClick={() => { setEditSettingKey(""); setEditSettingValue(""); setEditing(false); }}>取消</button>
            <button style={btnPrimary} onClick={handleSave}>保存</button>
          </div>
        </div>
      );
    }

    return null;
  };

  // ── Render ──
  return (
    <div style={{ borderTop: "1px solid #e0e0e0", marginTop: 8, paddingTop: 4 }}>
      {/* 折叠开关 */}
      <div
        onClick={() => { setCollapsed(!collapsed); if (collapsed) clearSelection(); }}
        style={{
          cursor: "pointer",
          fontSize: 13,
          fontWeight: 600,
          padding: "4px 0",
          display: "flex",
          alignItems: "center",
          userSelect: "none",
        }}
      >
        <span style={{ marginRight: 4 }}>{collapsed ? "▶" : "▼"}</span>
        🏛️ 创作库
      </div>

      {!collapsed && (
        <div style={{ marginTop: 4 }}>
          {/* TabBar */}
          <div style={{ display: "flex", gap: 2, marginBottom: 6 }}>
            {([
              ["character", "👤人物"],
              ["location", "🌍地点"],
              ["setting", "📋设定"],
              ["foreshadow", "🔮伏笔"],
            ] as [TabKey, string][]).map(([k, label]) => (
              <button
                key={k}
                onClick={() => { setTab(k); clearSelection(); }}
                style={{
                  flex: 1,
                  padding: "3px 0",
                  fontSize: 11,
                  border: "none",
                  borderRadius: 3,
                  background: tab === k ? "#e3f2fd" : "transparent",
                  cursor: "pointer",
                  fontWeight: tab === k ? 600 : 400,
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {/* 编辑面板（列表上方） */}
          {renderEditPanel()}

          {/* 列表区 */}
          <div style={{ maxHeight: 200, overflow: "auto", fontSize: 12 }}>
            {tab === "character" && characters.map(renderCharacterRow)}
            {tab === "location" && locations.map(renderLocationRow)}
            {tab === "setting" && settings.map(renderSettingRow)}
            {tab === "foreshadow" && foreshadows.map(renderForeshadowRow)}
            {tab === "character" && characters.length === 0 && <EmptyHint />}
            {tab === "location" && locations.length === 0 && <EmptyHint />}
            {tab === "setting" && settings.length === 0 && <EmptyHint />}
            {tab === "foreshadow" && foreshadows.length === 0 && <EmptyHint />}
          </div>

          {/* 操作按钮 */}
          <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
            <button style={{ ...btnSmall, flex: 1 }} onClick={handleAdd}>+ 添加</button>
            <button
              style={{ ...btnSmall, flex: 1, opacity: selectedEntity ? 1 : 0.4 }}
              disabled={!selectedEntity}
              onClick={handleEdit}
            >
              ✏️ 编辑
            </button>
            <button
              style={{ ...btnSmall, flex: 1, opacity: selectedEntity ? 1 : 0.4, color: "#ea4335" }}
              disabled={!selectedEntity}
              onClick={handleDelete}
            >
              ✕ 删除
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ── 子组件 ──

const Row: FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div style={{ display: "flex", alignItems: "flex-start", gap: 6, marginBottom: 4 }}>
    <span style={{ width: 48, fontSize: 12, color: "#666", paddingTop: 4, flexShrink: 0 }}>{label}</span>
    <div style={{ flex: 1 }}>{children}</div>
  </div>
);

const EmptyHint: FC = () => (
  <div style={{ color: "#ccc", fontSize: 12, padding: "8px 0", textAlign: "center" }}>(空)</div>
);

// ── 样式常量 ──

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "4px 6px",
  fontSize: 12,
  border: "1px solid #d0d0d0",
  borderRadius: 3,
  outline: "none",
};

const btnPrimary: React.CSSProperties = {
  padding: "4px 12px",
  fontSize: 12,
  border: "none",
  borderRadius: 3,
  background: "#4285f4",
  color: "#fff",
  cursor: "pointer",
};

const btnSecondary: React.CSSProperties = {
  padding: "4px 12px",
  fontSize: 12,
  border: "1px solid #ccc",
  borderRadius: 3,
  background: "#fff",
  cursor: "pointer",
};

const btnSmall: React.CSSProperties = {
  padding: "3px 6px",
  fontSize: 11,
  border: "1px solid #d0d0d0",
  borderRadius: 3,
  background: "#fff",
  cursor: "pointer",
};
