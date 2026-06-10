import React from 'react';
import { useAppContext } from './context/AppContext';
import Dashboard from './components/Dashboard';
import LeftPanel from './components/LeftPanel';
import CenterPanel from './components/CenterPanel';
import RightPanel from './components/RightPanel';
import BottomBar from './components/BottomBar';
import ProjectSettingsPanel from './components/ProjectSettings';
import './styles/variables.css';
import './App.css';

const App: React.FC = () => {
  const { state } = useAppContext();

  if (!state.activeProjectId) {
    return <Dashboard />;
  }

  const leftClosed = !state.leftPanelOpen;
  const rightClosed = !state.rightPanelOpen;
  const cls = `app${leftClosed ? ' left-closed' : ''}${rightClosed ? ' right-closed' : ''}`;

  return (
    <div className={cls}>
      <LeftPanel />
      <CenterPanel />
      <RightPanel />
      <BottomBar />
      <ProjectSettingsPanel />
    </div>
  );
};

export default App;
