import React, { useState } from 'react';
import { useAppContext } from '../context/AppContext';
import './LeftPanel.css';

const CollapsibleSection: React.FC<{
  title: string; defaultOpen?: boolean; children: React.ReactNode; badge?: number;
}> = ({ title, defaultOpen = true, children, badge }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="left-section">
      <button className="section-header" onClick={() => setOpen(!open)} title={open ? '折叠' : '展开'}>
        <span className={`arrow ${open ? 'open' : ''}`}>&#9654;</span>
        <span className="section-title">{title}</span>
        {badge !== undefined && badge > 0 && <span className="section-badge">{badge}</span>}
      </button>
      {open && <div className="section-body">{children}</div>}
    </div>
  );
};

const LeftPanel: React.FC = () => {
  const { state, dispatch } = useAppContext();
  const {
    chapters, activeChapterId, projectSettings,
    selectedCharacterId, selectedLocation, leftPanelOpen, activeProjectId,
  } = state;

  const chars = projectSettings?.characters ?? [];
  const locs = projectSettings?.locations ?? [];

  const handleBack = () => dispatch({ type: 'RETURN_TO_DASHBOARD' });

  const handleAddChapter = async () => {
    if (!activeProjectId) return;
    const { apiClient } = await import('../api/client');
    const ch = await apiClient.createChapter(activeProjectId, '新章节');
    dispatch({ type: 'ADD_CHAPTER', payload: ch });
  };

  return (
    <div className={`left-panel${leftPanelOpen ? '' : ' collapsed'}`}>
      <button className="back-btn" onClick={handleBack} title="返回工作台">
        <span>&#8592;</span><span>返回工作台</span>
      </button>

      <div className="left-scroll">
        <CollapsibleSection title="章节列表" badge={chapters.length}>
          {chapters.length === 0 ? (
            <p className="empty-hint">点击下方按钮添加章节</p>
          ) : (
            <ul className="chapter-list">
              {chapters.map(ch => (
                <li key={ch.id}>
                  <button
                    className={`chapter-item ${ch.id === activeChapterId ? 'active' : ''}`}
                    onClick={() => dispatch({ type: 'SELECT_CHAPTER', payload: ch.id })}
                    title={ch.title}
                  >
                    <span className="chapter-icon">&#x1f4c4;</span>
                    <span className="chapter-title">{ch.title}</span>
                    <span className="chapter-count">{ch.text.length}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <button className="add-chapter-btn" onClick={handleAddChapter}>+ 新建章节</button>
        </CollapsibleSection>

        <CollapsibleSection title={`角色 (${chars.length})`} defaultOpen={chars.length > 0}>
          {chars.length === 0 ? (
            <p className="empty-hint">点击底部「项目设定」添加</p>
          ) : (
            <div className="character-chips">
              {chars.map(name => (
                <button
                  key={name}
                  className={`character-chip ${name === selectedCharacterId ? 'active' : ''}`}
                  onClick={() => dispatch({ type: 'SELECT_CHARACTER', payload: name })}
                >{name}</button>
              ))}
            </div>
          )}
        </CollapsibleSection>

        <CollapsibleSection title={`地点 (${locs.length})`} defaultOpen={false}>
          {locs.length === 0 ? (
            <p className="empty-hint">点击底部「项目设定」添加</p>
          ) : (
            <ul className="location-list">
              {locs.map(loc => (
                <li key={loc}>
                  <button
                    className={`location-item ${loc === selectedLocation ? 'active' : ''}`}
                    onClick={() => dispatch({ type: 'SELECT_LOCATION', payload: loc })}
                  >
                    <span className="loc-marker">&#x1f4cd;</span><span>{loc}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CollapsibleSection>
      </div>

      <div className="left-footer">
        <button className="settings-btn" onClick={() => dispatch({ type: 'TOGGLE_PROJECT_SETTINGS' })}>
          &#9881;&#xfe0f; 项目设定
        </button>
      </div>
    </div>
  );
};

export default LeftPanel;
