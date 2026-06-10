import React from 'react';
import { useAppContext } from '../context/AppContext';
import type { Conflict } from '../types';
import TabCompare from './TabCompare';
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

// ---------------------------------------------------------------------------
// TabAnalysis — unified scene analysis display
// ---------------------------------------------------------------------------

const TabAnalysis: React.FC = () => {
  const { state } = useAppContext();
  const a = state.currentAnalysis;
  if (!a) return <div className="empty-state"><div className="empty-icon">&#x1f50d;</div><p>暂无分析结果</p><p className="empty-hint">在编辑器输入文本后点击工具栏「分析」按钮</p></div>;

  const sa = a.scene_analysis;
  const entities = a.extracted_entities;
  const cr = a.engine_results?.character_engine;
  const wr = a.engine_results?.world_engine;
  const g = a.guardian_output;

  const createdChars = entities?.characters?.created ?? [];
  const createdLocs = entities?.locations?.created ?? [];

  return (
    <div className="tab-analysis">
      {/* ==== 事件推演（主结果，置顶） ==== */}
      {sa?.event_prediction && (
        <div className="prediction-hero">
          <h4 className="section-title">
            <span className="section-icon">&#x1f4d6;</span>事件推演
          </h4>
          <div className="prediction-text">{sa.event_prediction}</div>
        </div>
      )}

      {/* ==== 角色 & 地点（自动识别+创建） ==== */}
      {(sa?.characters?.length || sa?.locations?.length) && (
        <div className="analysis-section entity-section">
          <h4 className="section-title">
            <span className="section-icon">&#x1f465;</span>角色 & 地点
            {(createdChars.length > 0 || createdLocs.length > 0) && (
              <span className="section-badge auto-badge">已自动添加</span>
            )}
          </h4>
          {(createdChars.length > 0 || createdLocs.length > 0) && (
            <div className="auto-create-notice">
              &#x2705; 已自动添加到项目：
              {createdChars.map(c => <span key={c} className="tag-new char">&#x1f464; {c}</span>)}
              {createdLocs.map(l => <span key={l} className="tag-new loc">&#x1f3e0; {l}</span>)}
            </div>
          )}
          {sa.characters.length > 0 && (
            <div className="entity-row">
              <span className="entity-label">角色</span>
              <div className="entity-tags">
                {sa.characters.map(c => (
                  <span key={c} className={`entity-tag ${createdChars.includes(c) ? 'created' : 'existing'}`}>
                    {c}{createdChars.includes(c) ? ' ✨' : ''}
                  </span>
                ))}
              </div>
            </div>
          )}
          {sa.locations.length > 0 && (
            <div className="entity-row">
              <span className="entity-label">地点</span>
              <div className="entity-tags">
                {sa.locations.map(l => (
                  <span key={l} className={`entity-tag ${createdLocs.includes(l) ? 'created' : 'existing'}`}>
                    {l}{createdLocs.includes(l) ? ' ✨' : ''}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ==== 角色情感 PAD ==== */}
      {cr && (
        <div className="analysis-section">
          <h4 className="section-title">
            <span className="section-icon">&#x1f9e0;</span>角色情感 (PAD)
            <span className={`section-badge char-label ${!state.selectedCharacterId ? 'no-char' : ''}`}>
              {state.selectedCharacterId || '未指定角色'}
            </span>
          </h4>
          <div className="pad-chart">
            <PADBar label="愉悦度 P" value={cr.pad_state.pleasure} />
            <PADBar label="唤醒度 A" value={cr.pad_state.arousal} />
            <PADBar label="支配度 D" value={cr.pad_state.dominance} />
          </div>
          {cr.behavior_prediction && (
            <div className="prediction-box">
              <div className="prediction-main">
                <span className="pred-label">行为</span>
                <span className="pred-action">{cr.behavior_prediction.predicted_action}</span>
                <span className="pred-confidence">{Math.round(cr.behavior_prediction.confidence * 100)}%</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ==== 世界规则 ==== */}
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

      {/* ==== 冲突报告 ==== */}
      {g && g.alarm_level !== 'info' && (
        <div className={`alarm-banner alarm-${g.alarm_level}`}>
          {g.alarm_level === 'critical' ? '⚠️ 检测到严重冲突，建议立即审查' : 'ℹ️ 存在需要注意的问题'}
          <span className="alarm-action">需执行: {g.action_required}</span>
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
        {activeRightTab === 'history' && <TabHistory />}
        {activeRightTab === 'compare' && <TabCompare />}
        {activeRightTab === 'references' && <TabReferences />}
      </div>
    </div>
  );
};

export default RightPanel;
