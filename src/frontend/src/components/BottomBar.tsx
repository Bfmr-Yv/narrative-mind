import React from 'react';
import { useAppContext } from '../context/AppContext';
import './BottomBar.css';

const BottomBar: React.FC = () => {
  const { state } = useAppContext();
  const { costData, apiConnected, activeProjectId } = state;

  const usagePercent = (costData.currentMonth / costData.monthlyBudget) * 100;

  return (
    <div className="bottom-bar">
      <span className="bottom-item">
        ${costData.currentMonth.toFixed(2)}
        <span className="muted"> / ${costData.monthlyBudget.toFixed(0)}</span>
        <span className={`dot ${usagePercent > 80 ? 'warn' : ''}${usagePercent > 100 ? ' over' : ''}`} />
      </span>

      <span className="bottom-item muted">
        {activeProjectId ? '编辑模式' : '工作台'}
      </span>

      <span className="bottom-item">
        <span className={`api-dot ${apiConnected ? 'on' : 'off'}`} />
        <span className="muted">{apiConnected ? 'API 已连接' : '离线'}</span>
      </span>

      <span className="bottom-item muted">v3.1</span>
    </div>
  );
};

export default BottomBar;
