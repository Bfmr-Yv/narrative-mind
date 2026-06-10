import React, { useState, useEffect } from 'react';
import { useAppActions } from '../context/AppContext';
import type { ProjectSettings as PS } from '../types';
import './ProjectSettings.css';

const ProjectSettingsPanel: React.FC = () => {
  const { state, saveSettings, toggleProjectSettings } = useAppActions();
  const settings = state.projectSettings;
  if (!settings || !state.showProjectSettings) return null;

  return (
    <div className="settings-overlay" onClick={toggleProjectSettings}>
      <div className="settings-panel" onClick={e => e.stopPropagation()}>
        <SettingsForm
          settings={settings}
          onSave={saveSettings}
          onClose={toggleProjectSettings}
        />
      </div>
    </div>
  );
};

// =========================================================================
// Form (internal)
// =========================================================================

interface SettingsFormProps {
  settings: PS;
  onSave: (s: PS) => Promise<void>;
  onClose: () => void;
}

const SettingsForm: React.FC<SettingsFormProps> = ({ settings, onSave, onClose }) => {
  const [chars, setChars] = useState<string[]>(settings.characters);
  const [locs, setLocs] = useState<string[]>(settings.locations);
  const [newChar, setNewChar] = useState('');
  const [newLoc, setNewLoc] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setChars(settings.characters);
    setLocs(settings.locations);
  }, [settings]);

  const addChar = () => {
    const name = newChar.trim();
    if (!name || chars.includes(name)) return;
    setChars([...chars, name]);
    setNewChar('');
  };

  const removeChar = (name: string) => setChars(chars.filter(c => c !== name));

  const addLoc = () => {
    const name = newLoc.trim();
    if (!name || locs.includes(name)) return;
    setLocs([...locs, name]);
    setNewLoc('');
  };

  const removeLoc = (name: string) => setLocs(locs.filter(l => l !== name));

  const handleSave = async () => {
    setSaving(true);
    await onSave({ ...settings, characters: chars, locations: locs });
    setSaving(false);
  };

  return (
    <>
      <div className="settings-header">
        <h2>项目设定</h2>
        <button className="settings-close" onClick={onClose}>&times;</button>
      </div>

      <div className="settings-body">
        {/* Characters */}
        <section className="settings-section">
          <h3>角色列表 ({chars.length})</h3>
          <div className="tag-list">
            {chars.map(name => (
              <span key={name} className="tag-item">
                {name}
                <button className="tag-remove" onClick={() => removeChar(name)}>&times;</button>
              </span>
            ))}
          </div>
          <div className="add-row">
            <input
              className="add-input"
              value={newChar}
              onChange={e => setNewChar(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addChar()}
              placeholder="输入角色名"
            />
            <button className="add-btn" onClick={addChar}>添加</button>
          </div>
        </section>

        {/* Locations */}
        <section className="settings-section">
          <h3>地点列表 ({locs.length})</h3>
          <div className="tag-list">
            {locs.map(name => (
              <span key={name} className="tag-item loc">
                <span className="loc-dot">&#x1f4cd;</span>
                {name}
                <button className="tag-remove" onClick={() => removeLoc(name)}>&times;</button>
              </span>
            ))}
          </div>
          <div className="add-row">
            <input
              className="add-input"
              value={newLoc}
              onChange={e => setNewLoc(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addLoc()}
              placeholder="输入地点名"
            />
            <button className="add-btn" onClick={addLoc}>添加</button>
          </div>
        </section>

        {/* Power system info (read-only for now) */}
        <section className="settings-section">
          <h3>力量体系</h3>
          <div className="power-info">
            {(settings.power_system as any)?.levels?.map((lvl: any, i: number) => (
              <div key={i} className="power-level-row">
                <span className="lvl-name">{lvl.name}</span>
                <span className="lvl-cap">{lvl.capabilities?.join('、')}</span>
              </div>
            ))}
            <p className="power-hint">力量体系编辑将在后续版本开放</p>
          </div>
        </section>
      </div>

      <div className="settings-footer">
        <button className="sett-cancel" onClick={onClose}>取消</button>
        <button className="sett-save" onClick={handleSave} disabled={saving}>
          {saving ? '保存中...' : '保存设定'}
        </button>
      </div>
    </>
  );
};

export default ProjectSettingsPanel;
