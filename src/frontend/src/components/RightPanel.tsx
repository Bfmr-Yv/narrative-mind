import React, { useState } from 'react';
import { useAppContext } from '../context/AppContext';
import type { Conflict, EntitySuggestion } from '../types';
import TabCompare from './TabCompare';
import { apiClient } from '../api/client';
import './RightPanel.css';

const PADBar: React.FC<{ label: string; value: number }> = ({ label, value }) => {
  const pct = ((value + 1) / 2) * 100;
  const color = value >= 0 ? 'var(--success)' : 'var(--danger)';
  return (
    <div className="pad-row">
      <span className="pad-label">{label}</span>
      <div className="pad-track"><div className="pad-fill" style={{ width: `${pct}%`, background: color }} /></div>
      <span className="pad-value">{value.toFixed(2)}</span>
    </div>
  );
};

const ConflictCard: React.FC<{ conflict: Conflict }> = ({ conflict }) => {
  const colors: Record<string, string> = { critical: 'var(--danger)', warn: 'var(--warning)', info: 'var(--primary)' };
  return (
    <div className="conflict-card" style={{ borderLeftColor: colors[conflict.level] || 'var(--light-border)' }}>
      <div className="conflict-meta">
        <span className="conflict-dim">{conflict.dimension}</span>
        <span className={`conflict-level level-${conflict.level}`}>{conflict.level}</span>
      </div>
      <p className="conflict-detail">{conflict.detail}</p>
      {conflict.suggestion && <p className="conflict-suggestion">&#x1f4a1; {conflict.suggestion}</p>}
    </div>
  );
};

const TabAnalysis: React.FC = () => {
  const { state } = useAppContext();
  const a = state.currentAnalysis;
  if (!a) return <div className="empty-state"><div className="empty-icon">&#x1f50d;</div><p>暂无分析结果</p><p className="empty-hint">在编辑器输入文本后点击工具栏「分析」按钮</p></div>;

  const cr = a.engine_results?.character_engine;
  const wr = a.engine_results?.world_engine;
  const g = a.guardian_output;

  // Resolve character name for PAD label
  const charName = state.selectedCharacterId || '未指定角色';

  return (
    <div className="tab-analysis">
      {g && g.alarm_level !== 'info' && (
        <div className={`alarm-banner alarm-${g.alarm_level}`}>
          {g.alarm_level === 'critical' ? '⚠️ 检测到严重冲突，建议立即审查' : 'ℹ️ 存在需要注意的问题'}
          <span className="alarm-action">需执行: {g.action_required}</span>
        </div>
      )}
      {cr && (
        <div className="analysis-section">
          <h4 className="section-title">
            <span className="section-icon">&#x1f9e0;</span>角色情感 (PAD)
            <span className="section-badge char-label">{charName}</span>
            {cr.needs_human_review ? <span className="section-badge">需审查</span> : null}
          </h4>
          {/* Hint when no character selected */}
          {!state.selectedCharacterId && (
            <div className="no-char-hint">
              &#x1f4a1; 尚未指定分析角色，请先在工具栏选择角色。
              如无角色可选，点击工具栏 <strong>「&#x1f50d; 发现」</strong> 按钮自动扫描。
            </div>
          )}
          <div className="pad-chart">
            <PADBar label="愉悦度 P" value={cr.pad_state.pleasure} />
            <PADBar label="唤醒度 A" value={cr.pad_state.arousal} />
            <PADBar label="支配度 D" value={cr.pad_state.dominance} />
          </div>
          {cr.behavior_prediction && (
            <div className="prediction-box">
              <div className="prediction-main">
                <span className="pred-label">预测</span>
                <span className="pred-action">{cr.behavior_prediction.predicted_action}</span>
                <span className="pred-confidence">{Math.round(cr.behavior_prediction.confidence * 100)}%</span>
              </div>
              {cr.behavior_prediction.alternative_actions.length > 0 && (
                <div className="prediction-alt">备选: {cr.behavior_prediction.alternative_actions.join(' / ')}</div>
              )}
            </div>
          )}
          {cr.implicit_triggers.length > 0 && (
            <div className="trigger-tags">{cr.implicit_triggers.map((t, i) => <span key={i} className="tag">{t}</span>)}</div>
          )}
        </div>
      )}
      {wr && (
        <div className="analysis-section">
          <h4 className="section-title"><span className="section-icon">&#x1f30d;</span>世界规则</h4>
          {wr.rule_checks.length === 0 ? <p className="no-data">暂无匹配的规则检查</p> : (
            <ul className="rule-list">
              {wr.rule_checks.map((r, i) => (
                <li key={i} className={`rule-row ${r.passed ? 'passed' : 'failed'}`}>
                  <span className="rule-icon">{r.passed ? '✅' : '❌'}</span>
                  <div className="rule-info">
                    <span className="rule-name">{r.rule_name}</span>
                    <span className="rule-detail">{r.detail}</span>
                    {r.conflict_description && <span className="rule-conflict">{r.conflict_description}</span>}
                  </div>
                </li>
              ))}
            </ul>
          )}
          <div className="world-summary">
            <span className={`chip ${wr.spatial_consistency ? 'ok' : 'warn'}`}>空间: {wr.spatial_consistency ? '一致' : '冲突'}</span>
            <span className="chip neutral">力量: {wr.power_level_validation}</span>
          </div>
        </div>
      )}
      {g && g.conflicts.length > 0 && (
        <div className="analysis-section">
          <h4 className="section-title"><span className="section-icon">&#x26a0;&#xfe0f;</span>冲突报告 ({g.conflicts.length})</h4>
          {g.conflicts.map((c, i) => <ConflictCard key={i} conflict={c} />)}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Entity Suggestions (Item 2) — standalone, used by TabDiscover and TabAnalysis
// ---------------------------------------------------------------------------

const EntitySuggestions: React.FC<{ embedded?: boolean }> = ({ embedded }) => {
  const { state, dispatch } = useAppContext();
  const [suggestions, setSuggestions] = useState<EntitySuggestion[]>([]);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');
  const [scanned, setScanned] = useState(false);

  const handleScan = async () => {
    if (!state.activeProjectId || !state.activeChapterId) return;
    setScanning(true);
    setError('');
    try {
      const result = await apiClient.suggestEntities(state.activeProjectId, {
        chapter_id: state.activeChapterId,
      });
      if (result.error) {
        setError(result.error);
      } else {
        setSuggestions(result.suggestions);
        setScanned(true);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '扫描失败');
    }
    setScanning(false);
  };

  const handleAdd = async (name: string, type: 'character' | 'location') => {
    if (!state.activeProjectId || !state.projectSettings) return;
    const updated = { ...state.projectSettings };
    if (type === 'character') {
      updated.characters = Array.from(new Set([...updated.characters, name]));
    } else {
      updated.locations = Array.from(new Set([...updated.locations, name]));
    }
    try {
      const saved = await apiClient.saveProjectSettings(state.activeProjectId, updated);
      dispatch({ type: 'SET_PROJECT_SETTINGS', payload: saved });
      setSuggestions(prev => prev.filter(s => s.name !== name));
    } catch { /* ignored */ }
  };

  if (!state.activeChapterId && !embedded) {
    return (
      <div className="empty-state">
        <div className="empty-icon">&#x1f50d;</div>
        <p>请先创建章节并输入文本</p>
        <p className="empty-hint">在章节中输入文本后，可自动扫描其中的角色和地点</p>
      </div>
    );
  }

  return (
    <div className={embedded ? 'analysis-section' : 'tab-discover'}>
      {!embedded && (
        <>
          <div className="discover-hero">
            <div className="discover-hero-icon">&#x1f50d;</div>
            <h3>发现角色与地点</h3>
            <p>AI 将自动扫描章节文本，识别其中的人物名称和地点名称</p>
          </div>
          <div className="discover-info">
            <div className="discover-info-item">
              <span className="discover-info-icon">&#x1f464;</span>
              <span>已知角色: {state.projectSettings?.characters?.length ?? 0} 个</span>
            </div>
            <div className="discover-info-item">
              <span className="discover-info-icon">&#x1f3e0;</span>
              <span>已知地点: {state.projectSettings?.locations?.length ?? 0} 个</span>
            </div>
          </div>
        </>
      )}
      {!embedded && (
        <h4 className="section-title">
          <span className="section-icon">&#x1f4d6;</span>扫描结果
        </h4>
      )}
      {!scanned ? (
        <button
          className="scan-btn"
          onClick={handleScan}
          disabled={scanning || !state.activeChapterId}
        >
          {scanning ? '⏳ AI 正在扫描文本...' : '🔍 扫描角色与地点'}
        </button>
      ) : error ? (
        <p className="scan-error">{error}</p>
      ) : suggestions.length === 0 ? (
        <div className="scan-empty">
          <span className="scan-empty-icon">&#x2705;</span>
          <p>未发现新的角色或地点</p>
          <p className="empty-hint">当前文本中的角色和地点都已在项目设定中</p>
        </div>
      ) : (
        <div className="suggestion-list">
          {suggestions.map((s, i) => (
            <div key={i} className="suggestion-card">
              <div className="suggestion-header">
                <span className="suggestion-name">{s.name}</span>
                <span className={`suggestion-type type-${s.type}`}>
                  {s.type === 'character' ? '👤 角色' : '📍 地点'}
                </span>
                <button
                  className="suggestion-add-btn"
                  onClick={() => handleAdd(s.name, s.type)}
                >
                  + 添加
                </button>
              </div>
              <div className="suggestion-context">{s.context}</div>
            </div>
          ))}
        </div>
      )}
      {scanned && (
        <button
          className="scan-btn scan-btn-secondary"
          onClick={handleScan}
          disabled={scanning || !state.activeChapterId}
          style={{ marginTop: '0.75rem' }}
        >
          {scanning ? '扫描中…' : '重新扫描'}
        </button>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// TabDiscover — standalone entity scan tab
// ---------------------------------------------------------------------------

const TabDiscover: React.FC = () => <EntitySuggestions embedded={false} />;

// ---------------------------------------------------------------------------
// TabHistory
// ---------------------------------------------------------------------------

const TabHistory: React.FC = () => {
  const { state, dispatch } = useAppContext();
  const h = state.analysisHistory;
  if (h.length === 0) return <div className="empty-state"><div className="empty-icon">&#x1f4dc;</div><p>暂无分析记录</p><p className="empty-hint">完成首次分析后，历史记录将在此显示</p></div>;
  return (
    <div className="tab-history">
      {h.map(e => {
        const g = e.response.guardian_output;
        const lv = g ? g.alarm_level : 'info';
        return (
          <button key={e.id} className="history-card" onClick={() => dispatch({ type: 'SELECT_HISTORY_ENTRY', payload: e.id })}>
            <div className="history-header">
              <span className="history-time">{e.timestamp.toLocaleTimeString('zh-CN')}</span>
              <span className={`history-level level-${lv}`}>{lv}</span>
            </div>
            <div className="history-info"><span>角色: {e.characterId || '(无)'}</span><span>地点: {e.location || '(无)'}</span></div>
            <div className="history-summary">{e.response.message}</div>
          </button>
        );
      })}
    </div>
  );
};

const TabReferences: React.FC = () => {
  const { state } = useAppContext();
  const ev = state.currentAnalysis?.engine_results?.character_engine?.behavior_prediction?.supporting_evidence;
  return (
    <div className="tab-references">
      <div className="empty-state"><div className="empty-icon">&#x1f4da;</div><p>语料参考</p><p className="empty-hint">语料参考浏览功能将在 Phase 2 开放</p></div>
      {ev && ev.length > 0 && (
        <div className="analysis-section">
          <h4 className="section-title">当前分析引用</h4>
          <ul className="evidence-list">{ev.map((s, i) => <li key={i} className="evidence-item">{s}</li>)}</ul>
        </div>
      )}
    </div>
  );
};

const RightPanel: React.FC = () => {
  const { state, dispatch } = useAppContext();
  const { activeRightTab, currentAnalysis, analysisHistory, rightPanelOpen } = state;
  const tabs = [
    { key: 'analysis' as const, label: '分析', count: currentAnalysis ? 1 : 0 },
    { key: 'discover' as const, label: '发现', count: 0 },
    { key: 'history' as const, label: '历史', count: analysisHistory.length },
    { key: 'compare' as const, label: '对比', count: state.compareSlotA && state.compareSlotB ? 1 : 0 },
    { key: 'references' as const, label: '参考', count: 0 },
  ];

  return (
    <div className={`right-panel${rightPanelOpen ? '' : ' collapsed'}`}>
      <div className="tab-bar">
        {tabs.map(t => (
          <button key={t.key} className={`tab-btn ${activeRightTab === t.key ? 'active' : ''}`} onClick={() => dispatch({ type: 'SELECT_TAB', payload: t.key })}>
            {t.label}{t.count > 0 && <span className="tab-badge">{t.count}</span>}
          </button>
        ))}
      </div>
      <div className="tab-content">
        {activeRightTab === 'analysis' && <TabAnalysis />}
        {activeRightTab === 'discover' && <TabDiscover />}
        {activeRightTab === 'history' && <TabHistory />}
        {activeRightTab === 'compare' && <TabCompare />}
        {activeRightTab === 'references' && <TabReferences />}
      </div>
    </div>
  );
};

export default RightPanel;
