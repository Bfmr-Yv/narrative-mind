import React from 'react';
import { useAppContext } from '../context/AppContext';
import './BottomBar.css';

const BottomBar: React.FC = () => {
  const { state } = useAppContext();
  const { costData, apiConnected, activeProjectId } = state;

  const usagePercent = costData.monthly_budget > 0
    ? (costData.monthly_spend / costData.monthly_budget) * 100
    : 0;
  const meltdownDot = costData.meltdown_level === 'blocked' ? 'dot blocked'
    : costData.meltdown_level === 'restricted' ? 'dot warn'
    : costData.meltdown_level === 'warning' ? 'dot warn'
    : 'dot';

  const meltdownLabel: Record<string, string> = {
    normal: '正常', warning: '警告', restricted: '受限', blocked: '熔断',
  };

  const byTask = Object.entries(costData.by_task_type);
  const tooltipText = byTask.length > 0
    ? '费用明细:\n' + byTask.map(([k, v]) => `${k}: $${v.toFixed(4)}`).join('\n')
    : '';

  return (
    <div className="bottom-bar">
      <span className="bottom-item" title={tooltipText}>
        ${costData.monthly_spend.toFixed(4)}
        <span className="muted"> / ${costData.monthly_budget.toFixed(0)}</span>
        <span className="muted"> ({usagePercent.toFixed(0)}%)</span>
        <span className={meltdownDot} />
      </span>

      <span className={`bottom-item meltdown-badge meltdown-${costData.meltdown_level}`}>
        {meltdownLabel[costData.meltdown_level] || costData.meltdown_level}
      </span>

      <span className="bottom-item muted">
        {activeProjectId ? '编辑模式' : '工作台'}
      </span>

      <span className="bottom-item muted" title={tooltipText}>
        调用: {costData.call_count}
      </span>

      <span className="bottom-item">
        <span className={`api-dot ${apiConnected ? 'on' : 'off'}`} />
        <span className="muted">{apiConnected ? 'API' : '离线'}</span>
      </span>

      <span className="bottom-item muted">v3.1</span>
    </div>
  );
};

export default BottomBar;
