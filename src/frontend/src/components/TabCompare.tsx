import React from 'react';
import { useAppContext } from '../context/AppContext';
import type { AnalysisHistoryEntry, OrchestratorResponse } from '../types';
import './TabCompare.css';

// ---------------------------------------------------------------------------
// Helper: extract comparison data from an entry
// ---------------------------------------------------------------------------

interface SlotData {
  id: string;
  timestamp: string;
  characterId: string;
  pad: { pleasure: number; arousal: number; dominance: number } | null;
  predictedAction: string;
  confidence: number;
  alarmLevel: string;
  conflictCount: number;
  conflicts: { dimension: string; level: string; detail: string }[];
}

function extractSlot(entry: AnalysisHistoryEntry): SlotData {
  const r: OrchestratorResponse = entry.response;
  const cr = r.engine_results?.character_engine;
  const g = r.guardian_output;
  return {
    id: entry.id,
    timestamp: entry.timestamp.toLocaleString('zh-CN'),
    characterId: entry.characterId,
    pad: cr?.pad_state ?? null,
    predictedAction: cr?.behavior_prediction?.predicted_action ?? '(无)',
    confidence: cr?.confidence ?? 0,
    alarmLevel: g?.alarm_level ?? 'info',
    conflictCount: g?.conflicts?.length ?? 0,
    conflicts: g?.conflicts ?? [],
  };
}

// ---------------------------------------------------------------------------
// Delta badge
// ---------------------------------------------------------------------------

const Delta: React.FC<{ value: number }> = ({ value }) => {
  const color = value > 0 ? 'var(--success)' : value < 0 ? 'var(--danger)' : 'var(--text-muted)';
  const prefix = value > 0 ? '+' : '';
  return <span className="delta" style={{ color }}>{prefix}{value.toFixed(2)}</span>;
};

// ---------------------------------------------------------------------------
// PAD bar (same as RightPanel but reused here for independence)
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const TabCompare: React.FC = () => {
  const { state, dispatch } = useAppContext();
  const { analysisHistory, compareSlotA, compareSlotB } = state;

  // Handler: select an entry for a slot
  const selectForSlot = (slot: 'A' | 'B', entryId: string) => {
    dispatch({ type: 'SELECT_COMPARE_SLOT', payload: { slot, entryId } });
  };

  // Resolve selected entries
  const entryA = compareSlotA ?? (analysisHistory.length >= 2 ? analysisHistory[1] : analysisHistory[0] ?? null);
  const entryB = compareSlotB ?? (analysisHistory.length >= 1 ? analysisHistory[0] : null);

  if (analysisHistory.length < 2) {
    return (
      <div className="empty-state">
        <div className="empty-icon">&#x1f504;</div>
        <p>需要至少 2 条分析记录才能对比</p>
        <p className="empty-hint">对同一章节进行多次分析后，在此对比结果变化</p>
      </div>
    );
  }

  const slotA = entryA ? extractSlot(entryA) : null;
  const slotB = entryB ? extractSlot(entryB) : null;

  return (
    <div className="tab-compare">
      {/* Slot selectors */}
      <div className="compare-selectors">
        <div className="compare-selector">
          <label>基准 A</label>
          <select value={entryA?.id ?? ''} onChange={e => selectForSlot('A', e.target.value)}>
            {analysisHistory.map(e => (
              <option key={e.id} value={e.id}>
                {e.timestamp.toLocaleTimeString('zh-CN')} — {e.characterId || '(无角色)'}
              </option>
            ))}
          </select>
        </div>
        <span className="compare-vs">VS</span>
        <div className="compare-selector">
          <label>对比 B</label>
          <select value={entryB?.id ?? ''} onChange={e => selectForSlot('B', e.target.value)}>
            {analysisHistory.map(e => (
              <option key={e.id} value={e.id}>
                {e.timestamp.toLocaleTimeString('zh-CN')} — {e.characterId || '(无角色)'}
              </option>
            ))}
          </select>
        </div>
      </div>

      {!slotA || !slotB ? (
        <p className="compare-placeholder">请选择两条分析记录进行对比</p>
      ) : (
        <div className="compare-content">
          {/* Confidence row */}
          <div className="compare-section">
            <h4 className="section-title">
              <span className="section-icon">&#x1f4ca;</span>置信度
            </h4>
            <div className="compare-dual">
              <div className="compare-col">
                <span className="compare-label">A: {slotA.timestamp}</span>
                <span className="compare-value">{Math.round(slotA.confidence * 100)}%</span>
              </div>
              <div className="compare-col">
                <span className="compare-label">B: {slotB.timestamp}</span>
                <span className="compare-value">{Math.round(slotB.confidence * 100)}%</span>
                <span className="compare-delta">
                  变化: <Delta value={slotB.confidence - slotA.confidence} />
                </span>
              </div>
            </div>
          </div>

          {/* PAD comparison */}
          <div className="compare-section">
            <h4 className="section-title">
              <span className="section-icon">&#x1f9e0;</span>PAD 情感对比
              {slotA.pad && slotB.pad && (
                <span className="section-badge">
                  P: <Delta value={slotB.pad.pleasure - slotA.pad.pleasure} />
                  {' '}A: <Delta value={slotB.pad.arousal - slotA.pad.arousal} />
                  {' '}D: <Delta value={slotB.pad.dominance - slotA.pad.dominance} />
                </span>
              )}
            </h4>
            <div className="compare-dual">
              <div className="compare-col">
                <span className="compare-label">A</span>
                {slotA.pad ? (
                  <>
                    <PADBar label="愉悦度 P" value={slotA.pad.pleasure} />
                    <PADBar label="唤醒度 A" value={slotA.pad.arousal} />
                    <PADBar label="支配度 D" value={slotA.pad.dominance} />
                  </>
                ) : <p className="no-data">无 PAD 数据</p>}
              </div>
              <div className="compare-col">
                <span className="compare-label">B</span>
                {slotB.pad ? (
                  <>
                    <PADBar label="愉悦度 P" value={slotB.pad.pleasure} />
                    <PADBar label="唤醒度 A" value={slotB.pad.arousal} />
                    <PADBar label="支配度 D" value={slotB.pad.dominance} />
                  </>
                ) : <p className="no-data">无 PAD 数据</p>}
              </div>
            </div>
          </div>

          {/* Behavior comparison */}
          <div className="compare-section">
            <h4 className="section-title">
              <span className="section-icon">&#x1f3af;</span>行为预测
              {slotA.predictedAction !== slotB.predictedAction && (
                <span className="section-badge changed">已变化</span>
              )}
            </h4>
            <div className="compare-dual">
              <div className="compare-col">
                <span className="compare-label">A</span>
                <span className="compare-action">{slotA.predictedAction}</span>
              </div>
              <div className="compare-col">
                <span className="compare-label">B</span>
                <span className="compare-action">{slotB.predictedAction}</span>
              </div>
            </div>
          </div>

          {/* Conflict comparison */}
          <div className="compare-section">
            <h4 className="section-title">
              <span className="section-icon">&#x26a0;&#xfe0f;</span>冲突对比
              {slotA.conflictCount !== slotB.conflictCount && (
                <span className="section-badge">
                  {slotB.conflictCount > slotA.conflictCount ? '+' : ''}
                  {slotB.conflictCount - slotA.conflictCount}
                </span>
              )}
            </h4>
            <div className="compare-dual">
              <div className="compare-col">
                <span className="compare-label">A ({slotA.conflictCount} 冲突, {slotA.alarmLevel})</span>
                {slotA.conflicts.map((c, i) => (
                  <div key={i} className={`conflict-mini level-${c.level}`}>
                    <span className="conflict-dim">{c.dimension}</span>
                    <span className="conflict-text">{c.detail.slice(0, 60)}{c.detail.length > 60 ? '…' : ''}</span>
                  </div>
                ))}
              </div>
              <div className="compare-col">
                <span className="compare-label">B ({slotB.conflictCount} 冲突, {slotB.alarmLevel})</span>
                {slotB.conflicts.map((c, i) => (
                  <div key={i} className={`conflict-mini level-${c.level}`}>
                    <span className="conflict-dim">{c.dimension}</span>
                    <span className="conflict-text">{c.detail.slice(0, 60)}{c.detail.length > 60 ? '…' : ''}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TabCompare;
