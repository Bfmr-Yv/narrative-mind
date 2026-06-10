import React, { useRef, useCallback, useEffect, useState } from 'react';
import { useAppContext, useAppActions } from '../context/AppContext';
import './CenterPanel.css';

const AUTOSAVE_DELAY = 2000; // 2 秒无输入后自动保存

const CenterPanel: React.FC = () => {
  const { state, dispatch } = useAppContext();
  const { saveChapter, runAnalysis, selectCharacter } = useAppActions();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved');

  const activeChapter = state.chapters.find(ch => ch.id === state.activeChapterId);
  const chapterText = activeChapter?.text ?? '';
  const chapterTitle = activeChapter?.title ?? '';
  const activeChapterId = state.activeChapterId;

  // 融合多数据源的角色/地点列表（projectSettings + 当前分析结果）
  const settingsChars = state.projectSettings?.characters ?? [];
  const settingsLocs = state.projectSettings?.locations ?? [];
  const analysisChars = state.currentAnalysis?.scene_analysis?.characters ?? [];
  const analysisLocs = state.currentAnalysis?.scene_analysis?.locations ?? [];
  const entityChars = state.currentAnalysis?.extracted_entities?.characters?.found ?? [];
  const entityLocs = state.currentAnalysis?.extracted_entities?.locations?.found ?? [];
  // 去重合并：settings 排前面（已持久化的优先）
  const chars = Array.from(new Set([...settingsChars, ...analysisChars, ...entityChars]));
  const locs = Array.from(new Set([...settingsLocs, ...analysisLocs, ...entityLocs]));

  // 自动保存：文本或标题变化后 2 秒触发
  useEffect(() => {
    if (!activeChapterId) return;
    setSaveStatus('unsaved');

    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(async () => {
      setSaveStatus('saving');
      try {
        await saveChapter(activeChapterId, chapterTitle, chapterText);
        setSaveStatus('saved');
      } catch {
        setSaveStatus('unsaved');
      }
    }, AUTOSAVE_DELAY);

    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [chapterText, chapterTitle, activeChapterId, saveChapter]);

  // Gather dispatch helpers inline (avoids circular dependency with AppContext)
  const updateTitle = useCallback(
    (title: string) => {
      if (state.activeChapterId) {
        dispatch({ type: 'UPDATE_CHAPTER_TITLE', payload: { id: state.activeChapterId, title } });
      }
    },
    [state.activeChapterId, dispatch]
  );

  const updateText = useCallback(
    (text: string) => {
      if (state.activeChapterId) {
        dispatch({ type: 'UPDATE_CHAPTER_TEXT', payload: { id: state.activeChapterId, text } });
      }
    },
    [state.activeChapterId, dispatch]
  );

  const handleAnalyze = useCallback(() => {
    if (!chapterText.trim() || state.isAnalyzing) return;

    // 分析前先保存当前内容
    if (activeChapterId) {
      saveChapter(activeChapterId, chapterTitle, chapterText).catch(() => {});
    }

    runAnalysis();
  }, [chapterText, chapterTitle, activeChapterId, state.isAnalyzing, saveChapter, runAnalysis]);

  const handleImport = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        const text = reader.result as string;
        updateText(text);
        // Try to extract filename as title
        const name = file.name.replace(/\.[^.]+$/, '');
        if (name && name !== chapterTitle) {
          updateTitle(name);
        }
      };
      reader.readAsText(file, 'UTF-8');
      e.target.value = '';
    },
    [updateText, updateTitle, chapterTitle]
  );

  const wordCount = chapterText.length;

  return (
    <div className="center-panel">
      {/* Toolbar */}
      <div className="toolbar">
        <button
          className="toggle-btn"
          onClick={() => dispatch({ type: 'TOGGLE_LEFT_PANEL' })}
          title={state.leftPanelOpen ? '收起侧边栏' : '展开侧边栏'}
        >
          &#9776;
        </button>

        <input
          className="toolbar-title"
          type="text"
          value={chapterTitle}
          onChange={e => updateTitle(e.target.value)}
          placeholder="章节标题"
        />

        <div className="toolbar-spacer" />

        <select
          className="toolbar-select"
          value={state.selectedCharacterId}
          onChange={e => selectCharacter(e.target.value)}
          title="分析目标角色"
        >
          {chars.map(name => (
            <option key={name} value={name}>{name}</option>
          ))}
          {chars.length === 0 && <option value="">(无角色，请先在项目设定中添加)</option>}
        </select>

        <input
          className="toolbar-input"
          type="text"
          list="location-list"
          value={state.selectedLocation}
          onChange={e => dispatch({ type: 'SELECT_LOCATION', payload: e.target.value })}
          placeholder="地点"
          title="故事发生地点"
        />
        <datalist id="location-list">
          {locs.map(loc => (
            <option key={loc} value={loc} />
          ))}
        </datalist>

        <button
          className="import-btn"
          onClick={handleImport}
          title="导入 Markdown/TXT 文件"
        >
          导入
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".md,.txt,.text"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />

        <button
          className="analyze-btn"
          onClick={handleAnalyze}
          disabled={!chapterText.trim() || state.isAnalyzing}
        >
          {state.isAnalyzing ? '分析中...' : '分析'}
        </button>

        <button
          className="toggle-btn right"
          onClick={() => dispatch({ type: 'TOGGLE_RIGHT_PANEL' })}
          title={state.rightPanelOpen ? '收起分析面板' : '展开分析面板'}
        >
          &#9776;
        </button>
      </div>

      {/* Editor */}
      <textarea
        ref={textareaRef}
        className="editor-area"
        value={chapterText}
        onChange={e => updateText(e.target.value)}
        placeholder="开始书写你的故事..."
        spellCheck={false}
      />

      {/* Status bar */}
      <div className="editor-status">
        <span>字数: {wordCount.toLocaleString()}</span>
        <span className={`status-saved ${saveStatus}`}>
          {saveStatus === 'saved' ? '已自动保存' : saveStatus === 'saving' ? '保存中...' : '未保存'}
        </span>
        <span className={`status-dot ${state.apiConnected ? 'online' : 'offline'}`} />
      </div>
    </div>
  );
};

export default CenterPanel;
