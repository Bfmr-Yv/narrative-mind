import React, { useState } from 'react';
import { useAppActions } from '../context/AppContext';
import type { ProjectMeta } from '../types';
import './Dashboard.css';

const Dashboard: React.FC = () => {
  const { state, createProject, enterProject, deleteProject } = useAppActions();
  const [showNewDialog, setShowNewDialog] = useState(false);
  const [newName, setNewName] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleCreate = async () => {
    const name = newName.trim();
    if (!name) return;
    setNewName('');
    setShowNewDialog(false);
    const proj = await createProject(name);
    enterProject(proj.id);
  };

  const handleEnter = (id: string) => {
    enterProject(id);
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`确定要删除项目「${name}」吗？此操作不可恢复。`)) return;
    setDeletingId(id);
    await deleteProject(id);
    setDeletingId(null);
  };

  return (
    <div className="dashboard">
      <header className="dash-header">
        <div className="dash-brand">
          <span className="dash-icon">&#x1f4d6;</span>
          <div>
            <h1>Narrative Mind</h1>
            <p className="dash-sub">AI 辅助小说创作系统</p>
          </div>
        </div>
        <button className="dash-new-btn" onClick={() => setShowNewDialog(true)}>
          + 新建项目
        </button>
      </header>

      <main className="dash-main">
        {state.projects.length === 0 ? (
          <div className="dash-empty">
            <div className="empty-big-icon">&#x1f4dd;</div>
            <h2>欢迎使用 Narrative Mind</h2>
            <p>创建你的第一个项目，开始 AI 辅助创作之旅</p>
            <button className="dash-new-btn primary" onClick={() => setShowNewDialog(true)}>
              + 创建新项目
            </button>
          </div>
        ) : (
          <div className="project-grid">
            {state.projects.map(proj => (
              <div key={proj.id} className="project-card" onClick={() => handleEnter(proj.id)}>
                <div className="card-cover">
                  <span className="card-icon">&#x1f4d6;</span>
                </div>
                <div className="card-body">
                  <h3 className="card-title">{proj.name}</h3>
                  <div className="card-stats">
                    <span>{proj.chapter_count} 章</span>
                    <span>{proj.total_words.toLocaleString()} 字</span>
                  </div>
                  <div className="card-footer">
                    <span className="card-time">{proj.updated ? `最后编辑: ${proj.updated}` : ''}</span>
                    <button
                      className="card-delete"
                      onClick={e => {
                        e.stopPropagation();
                        handleDelete(proj.id, proj.name);
                      }}
                      disabled={deletingId === proj.id}
                      title="删除项目"
                    >
                      &#x1f5d1;
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* New project dialog */}
      {showNewDialog && (
        <div className="modal-overlay" onClick={() => setShowNewDialog(false)}>
          <div className="modal-box" onClick={e => e.stopPropagation()}>
            <h3>新建项目</h3>
            <input
              className="modal-input"
              type="text"
              placeholder="输入项目名称"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreate()}
              autoFocus
            />
            <div className="modal-actions">
              <button className="modal-cancel" onClick={() => setShowNewDialog(false)}>取消</button>
              <button className="modal-confirm" onClick={handleCreate} disabled={!newName.trim()}>
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
