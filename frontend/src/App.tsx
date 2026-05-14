import React, { useEffect, useState, useCallback, useRef } from 'react';
import { ReactFlowProvider } from 'reactflow';
import CanvasView from './canvas/CanvasView';
import BlockEditor from './panels/BlockEditor';
import StoryCardPicker from './panels/StoryCardPicker';
import WritingPanel from './panels/WritingPanel';
import LLMSettingsModal from './panels/LLMSettingsModal';
import SnapshotHistoryPanel from './panels/SnapshotHistoryPanel';
import TrackingPanel from './panels/TrackingPanel';
import BlockPoolPanel from './panels/BlockPoolPanel';
import ImportDialog from './panels/ImportDialog';
import LanguageSwitcher from './panels/LanguageSwitcher';
import { useProjectStore } from './store/projectStore';
import { useCanvasStore } from './store/canvasStore';
import { useUIStore } from './store/uiStore';
import * as exportApi from './api/export_import';
import * as snapshotsApi from './api/snapshots';
import * as blocksApi from './api/blocks';
import { BLOCK_LABELS, BLOCK_COLORS } from './types/blocks';
import { ViewMode } from './types/canvas';
import { useT } from './i18n/useT';
import { getCurrentLang } from './i18n';

type SaveStatus = 'saved' | 'saving' | 'failed';

const App: React.FC = () => {
  const { t } = useT();
  const { projects, currentProject, loadProjects, loadProject, createProject, progress, loadProgress } = useProjectStore();
  const { setViewMode, viewMode, selectedBlock } = useCanvasStore();
  const {
    showStoryCardPicker, showBlockEditor, showWritingPanel,
    showProjectList, showTrackingPanel, showBlockPool, showLLMSettings, activeTab,
    setShowStoryCardPicker, setShowBlockEditor, setShowWritingPanel,
    setShowProjectList, setShowTrackingPanel, setShowBlockPool, setShowLLMSettings, setActiveTab,
    toastMessage, toastType, showToast,
  } = useUIStore();

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newProjectTitle, setNewProjectTitle] = useState('');
  const [newProjectGenre, setNewProjectGenre] = useState('');

  // Save/Export/Import state
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('saved');
  const [showHistoryPanel, setShowHistoryPanel] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importPreviewData, setImportPreviewData] = useState<any>(null);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const dropRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreateProject = async () => {
    if (!newProjectTitle.trim()) {
      showToast('请输入项目名称', 'warning');
      return;
    }
    const id = await createProject(newProjectTitle.trim(), newProjectGenre || undefined);
    if (id) {
      setShowCreateForm(false);
      setNewProjectTitle('');
      setNewProjectGenre('');
      await loadProject(id);
      setShowStoryCardPicker(true);
      showToast('项目创建成功');
    }
  };

  const handleSelectProject = async (id: string) => {
    await loadProject(id);
    setShowProjectList(false);
  };

  const handleNewProject = () => {
    setShowCreateForm(true);
  };

  // Periodically check progress
  useEffect(() => {
    if (currentProject) {
      const interval = setInterval(() => {
        loadProgress(currentProject.id);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [currentProject?.id]);

  // Simulate save status (simplified: always saved after operations)
  useEffect(() => {
    if (currentProject) {
      setSaveStatus('saved');
    }
  }, [currentProject?.id, selectedBlock?.id]);

  // Context menu event listeners (from BaseBlock right-click)
  useEffect(() => {
    const handleDelete = (e: Event) => {
      const { blockId } = (e as CustomEvent).detail;
      if (currentProject) {
        useProjectStore.getState().removeBlock(currentProject.id, blockId);
        showToast('已删除块');
      }
    };
    const handleDuplicate = (e: Event) => {
      const { blockId, blockData } = (e as CustomEvent).detail;
      if (currentProject) {
        useProjectStore.getState().addBlock(currentProject.id, {
          type: blockData.type,
          canvas_x: blockData.canvas_x + 50,
          canvas_y: blockData.canvas_y + 50,
          content: { ...blockData.content },
        });
        showToast('已复制块');
      }
    };
    const handleEdit = (e: Event) => {
      const { blockId } = (e as CustomEvent).detail;
      useCanvasStore.getState().setSelectedBlock(blockId);
      setShowBlockEditor(true);
    };
    const handleAIFill = async (e: Event) => {
      const { blockId } = (e as CustomEvent).detail;
      if (currentProject) {
        showToast('AI生成中...');
        try {
          const res = await fetch(`/api/projects/${currentProject.id}/generate/block-content`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ block_id: blockId, field: 'all', hint: '' }),
          });
          if (res.ok) {
            const data = await res.json();
            const generated = data.generated_fields || {};
            const fieldCount = Object.keys(generated).length;
            // 更新块内容
            await useProjectStore.getState().updateBlock(currentProject.id, blockId, {
              content: data.merged_content,
            });
            showToast(`AI填充完成: ${fieldCount} 个字段`);
          } else {
            showToast('AI填充失败', 'error');
          }
        } catch {
          showToast('AI填充出错', 'error');
        }
      }
    };

    window.addEventListener('block:delete', handleDelete);
    window.addEventListener('block:duplicate', handleDuplicate);
    window.addEventListener('block:edit', handleEdit);
    window.addEventListener('block:ai-fill', handleAIFill);
    return () => {
      window.removeEventListener('block:delete', handleDelete);
      window.removeEventListener('block:duplicate', handleDuplicate);
      window.removeEventListener('block:edit', handleEdit);
      window.removeEventListener('block:ai-fill', handleAIFill);
    };
  }, [currentProject?.id]);

  const handleAddBlock = async (type: string) => {
    if (!currentProject) return;
    setSaveStatus('saving');
    const { addBlock } = useProjectStore.getState();
    await addBlock(currentProject.id, {
      type: type as any,
      canvas_x: 300 + Math.random() * 200,
      canvas_y: 200 + Math.random() * 300,
      content: {},
    });
    setSaveStatus('saved');
    showToast(`已添加 ${BLOCK_LABELS[type] || type} 块`);
  };

  // Export handlers
  const handleExport = (format: string) => {
    if (!currentProject) return;
    setShowExportMenu(false);
    if (format === 'storycanvas') exportApi.exportFull(currentProject.id);
    else if (format === 'canvas-json') exportApi.exportCanvasJson(currentProject.id);
    else if (format === 'markdown') exportApi.exportMarkdown(currentProject.id);
  };

  // Import handlers
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await showImportPreview(file);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (!file) return;
    await showImportPreview(file);
  };

  const showImportPreview = async (file: File) => {
    try {
      const preview = await exportApi.importPreview(file);
      setImportPreviewData(preview);
      setImportFile(file);
      setShowImportDialog(true);
    } catch (err: any) {
      showToast(err.message || '文件解析失败', 'error');
    }
  };

  const handleImportConfirm = async () => {
    if (!importFile) return;
    setImporting(true);
    try {
      const result = await exportApi.importProject(importFile);
      showToast(`导入成功: ${result.title}`);
      setShowImportDialog(false);
      setImportFile(null);
      setImportPreviewData(null);
      // Navigate to imported project if it was created
      if (result.project_id) {
        await loadProjects();
        await loadProject(result.project_id);
      }
    } catch (err: any) {
      showToast(err.message || '导入失败', 'error');
    }
    setImporting(false);
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  if (!currentProject) {
    return (
      <div className="app-layout">
        <div className="app-header">
          <div className="logo">🎨 StoryCanvas</div>
          <div className="header-actions">
            <button className="btn btn-primary" onClick={handleNewProject}>{t('project.new')}</button>
            {projects.length > 0 && (
              <button className="btn" onClick={() => setShowProjectList(true)}>
                {t('project.open')} ({projects.length})
              </button>
            )}
            <button className="btn btn-sm" onClick={() => setShowLLMSettings(true)} title={t('header.model_settings')}>
              🤖 {t('header.model_settings')}
            </button>
            <LanguageSwitcher />
          </div>
        </div>
        <div className="app-body">
          <div
            className="empty-state"
            style={{ flex: 1 }}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <h2 style={{ fontSize: 48 }}>🎨</h2>
            <h3>🎨 StoryCanvas</h3>
            <p>{t('welcome_desc')}</p>
            <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
              <button className="btn btn-primary" onClick={handleNewProject} style={{ padding: '10px 24px', fontSize: 15 }}>
                {t('project.new')}
              </button>
              {projects.length > 0 && (
                <button className="btn" onClick={() => setShowProjectList(true)} style={{ padding: '10px 24px', fontSize: 15 }}>
                  {t('project.open')}
                </button>
              )}

            </div>
          </div>
        </div>

        {showProjectList && (
          <div className="modal-overlay" onClick={() => setShowProjectList(false)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <h2>项目列表</h2>
              {projects.map((p) => (
                <div key={p.id} className="project-list-item" onClick={() => handleSelectProject(p.id)}>
                  <div className="project-info">
                    <div className="project-title">{p.title}</div>
                    <div className="project-meta">{p.genre || '未分类'} · 创建于 {p.created_at?.substring(0, 10)}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button
                      className="btn btn-sm"
                      style={{ color: '#E74C3C', fontSize: 11 }}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`确定删除项目「${p.title}」？此操作不可撤销。`)) {
                          useProjectStore.getState().deleteProject(p.id);
                          showToast('已删除项目');
                        }
                      }}
                    >
                      删除
                    </button>
                    <span style={{ color: '#4A90D9', fontSize: 12 }}>打开 →</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {showCreateForm && (
          <div className="modal-overlay" onClick={() => setShowCreateForm(false)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <h2>新建项目</h2>
              <div className="create-project-form">
                <div className="form-group">
                  <label className="form-label">项目名称 *</label>
                  <input className="form-input" value={newProjectTitle} onChange={(e) => setNewProjectTitle(e.target.value)} placeholder="给你的故事起个名字" autoFocus onKeyDown={(e) => e.key === 'Enter' && handleCreateProject()} />
                </div>
                <div className="form-group">
                  <label className="form-label">类型（可选）</label>
                  <input className="form-input" value={newProjectGenre} onChange={(e) => setNewProjectGenre(e.target.value)} placeholder="如：奇幻、科幻、悬疑..." />
                </div>
                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                  <button className="btn" onClick={() => setShowCreateForm(false)}>取消</button>
                  <button className="btn btn-primary" onClick={handleCreateProject}>创建项目</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {showLLMSettings && <LLMSettingsModal onClose={() => setShowLLMSettings(false)} onSave={() => showToast('设置已保存')} />}
        {toastMessage && (
          <div className="toast-container"><div className={`toast ${toastType}`}>{toastMessage}</div></div>
        )}
      </div>
    );
  }

  return (
    <div className="app-layout" ref={dropRef}
      onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}>
      {/* Drag overlay */}
      {dragOver && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          background: 'rgba(74, 144, 217, 0.15)',
          border: '3px dashed #4A90D9',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 24, fontWeight: 700, color: '#4A90D9',
          pointerEvents: 'none',
        }}>
          释放以导入
        </div>
      )}

      {/* Header */}
      <div className="app-header">
        <div className="logo" onClick={() => setShowProjectList(true)}>🎨 StoryCanvas</div>
        <span style={{ fontSize: 13, color: '#a0a0b0' }}>{currentProject.title}</span>

        {/* Save status indicator + button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 8 }}>
          <span style={{
            display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
            background: saveStatus === 'saved' ? '#50C878' : saveStatus === 'saving' ? '#F39C12' : '#E74C3C',
            animation: saveStatus === 'saving' ? 'pulse 1s infinite' : 'none',
          }} />
          <span style={{ fontSize: 11, color: saveStatus === 'saved' ? '#50C878' : saveStatus === 'saving' ? '#F39C12' : '#E74C3C' }}>
            {saveStatus === 'saved' ? '已保存' : saveStatus === 'saving' ? '保存中...' : '保存失败'}
          </span>
          <button className="btn btn-sm btn-ghost" style={{ fontSize: 10, padding: '2px 6px', marginLeft: 4 }}
            onClick={async () => {
              setSaveStatus('saving');
              try {
                // 先保存所有拖拽但未落盘的位置
                if (currentProject) {
                  await useCanvasStore.getState().saveDirtyPositions(currentProject.id);
                  await loadProject(currentProject.id);
                }
                setSaveStatus('saved');
              } catch {
                setSaveStatus('failed');
              }
            }}
            title="手动保存">💾</button>
        </div>

        <div style={{ display: 'flex', gap: 4, marginLeft: 16, alignItems: 'center' }}>
          <button className={`btn btn-sm ${activeTab === 'canvas' ? 'btn-primary' : ''}`} onClick={() => setActiveTab('canvas')}>画布</button>
          <button className={`btn btn-sm ${activeTab === 'writing' ? 'btn-primary' : ''}`} onClick={() => setActiveTab('writing')}>写作</button>
        </div>
        <div style={{ marginLeft: 16, display: 'flex', gap: 4 }}>
          <select className="form-select" value={viewMode} onChange={(e) => setViewMode(e.target.value as ViewMode)} style={{ fontSize: 12, padding: '4px 8px' }}>
            <option value="overview">全览模式</option>
            <option value="character_focus">角色聚焦</option>
            <option value="timeline">时间线模式</option>
            <option value="foreshadow_track">伏笔追踪</option>
            <option value="progress">进度模式</option>
            <option value="screenplay">剧本模式</option>
          </select>
        </div>

        <div className="header-actions">
          {/* Snapshot/History */}
          <button className="btn btn-sm" onClick={() => setShowHistoryPanel(!showHistoryPanel)} title="快照历史">
            ⏱
          </button>

          {/* Export dropdown */}
          <div style={{ position: 'relative' }}>
            <button className="btn btn-sm" onClick={() => setShowExportMenu(!showExportMenu)} title="导出">
              📤 导出
            </button>
            {showExportMenu && (
              <>
                <div style={{ position: 'fixed', inset: 0, zIndex: 100 }} onClick={() => setShowExportMenu(false)} />
                <div style={{
                  position: 'absolute', right: 0, top: 30, zIndex: 101,
                  background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
                  borderRadius: 6, padding: 4, minWidth: 160, boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
                }}>
                  {[
                    { key: 'storycanvas', icon: '📦', label: '.storycanvas (完整)' },
                    { key: 'canvas-json', icon: '📋', label: 'canvas.json (画布)' },
                    { key: 'markdown', icon: '📝', label: 'Markdown (全文)' },
                  ].map((item) => (
                    <div key={item.key} onClick={() => handleExport(item.key)}
                      style={{ padding: '7px 12px', cursor: 'pointer', borderRadius: 4, fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--hover-bg)')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}>
                      {item.icon} {item.label}
                    </div>
                  ))}
                  </div>
                </>
              )}
            </div>

          <button className="btn btn-sm" onClick={() => setShowStoryCardPicker(true)}>{t('header.story_card')}</button>
          <button className="btn btn-sm" onClick={() => setShowBlockPool(!showBlockPool)} title={t('header.block_pool')}>
            📦 {showBlockPool ? t('header.close_pool') : t('header.block_pool')}
          </button>
          <button className="btn btn-sm" onClick={() => setShowTrackingPanel(!showTrackingPanel)} title={t('header.tracking')}>
            📊 {showTrackingPanel ? t('header.close_tracking') : t('header.tracking')}
          </button>
          {activeTab === 'canvas' && (
            <button className="btn btn-sm" onClick={() => setShowWritingPanel(!showWritingPanel)}>
              {showWritingPanel ? t('writing.title') : t('header.writing')}
            </button>
          )}
          <button className="btn btn-sm" onClick={() => setShowImportModal(true)} title={t('header.import')}>📥 {t('header.import')}</button>
          <button className="btn btn-sm" onClick={() => setShowLLMSettings(true)} title={t('header.model_settings')}>🤖 {t('header.model_settings')}</button>
          <button className="btn btn-sm btn-primary" onClick={handleNewProject}>{t('project.new')}</button>
          <LanguageSwitcher />
        </div>
      </div>

      {/* Body */}
      <div className="app-body" style={{ position: 'relative' }}>
        {activeTab === 'canvas' && (
          <ReactFlowProvider>
            <CanvasView />
          </ReactFlowProvider>
        )}
        {activeTab === 'writing' && <WritingPanel />}

        {activeTab === 'canvas' && selectedBlock && <BlockEditor />}
        {showWritingPanel && activeTab === 'canvas' && <WritingPanel />}

        {/* History Panel */}
        {showHistoryPanel && <SnapshotHistoryPanel onClose={() => setShowHistoryPanel(false)} />}

        {/* Tracking Panel */}
        {showTrackingPanel && <TrackingPanel />}

        {/* Block Pool */}
        {showBlockPool && <BlockPoolPanel />}

        {/* Floating add block button - grouped menu for all 33 block types */}
        {activeTab === 'canvas' && (
          <AddBlockMenu onAdd={handleAddBlock} />
        )}
      </div>

      {showStoryCardPicker && <StoryCardPicker projectId={currentProject.id} onClose={() => setShowStoryCardPicker(false)} />}

      {showLLMSettings && <LLMSettingsModal onClose={() => setShowLLMSettings(false)} onSave={() => showToast('设置已保存')} />}

      {/* Import Dialog (new: 3-tab import) */}
      {showImportModal && <ImportDialog onClose={() => setShowImportModal(false)} />}

      {/* Import Dialog (old: .storycanvas/.json drag-drop) */}
      {showImportDialog && importPreviewData && (
        <div className="modal-overlay" onClick={() => { setShowImportDialog(false); setImportFile(null); setImportPreviewData(null); }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ width: 480 }}>
            <h2 style={{ marginBottom: 16 }}>📥 导入项目预览</h2>
            <div style={{ background: 'var(--bg-primary)', borderRadius: 8, padding: 16, marginBottom: 16 }}>
              <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>{importPreviewData.title}</div>
              <div style={{ fontSize: 13, color: '#a0a0b0', lineHeight: 1.8 }}>
                <div>📦 格式：{importPreviewData.format}</div>
                <div>🧱 块数量：{importPreviewData.total_blocks}</div>
                <div>📖 章节：{importPreviewData.total_chapters}</div>
                <div>📝 字数：{importPreviewData.total_words?.toLocaleString()}</div>
                {importPreviewData.exported_at && <div>🕐 导出时间：{importPreviewData.exported_at?.substring(0, 16)}</div>}
                {importPreviewData.story_cards?.length > 0 && <div>🎴 故事卡：{importPreviewData.story_cards.join(', ')}</div>}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button className="btn" onClick={() => { setShowImportDialog(false); setImportFile(null); setImportPreviewData(null); }}>取消</button>
              <button className="btn btn-primary" onClick={handleImportConfirm} disabled={importing}>
                {importing ? '导入中...' : '✅ 确认导入'}
              </button>
            </div>
          </div>
        </div>
      )}

      {toastMessage && (
        <div className="toast-container"><div className={`toast ${toastType}`}>{toastMessage}</div></div>
      )}
    </div>
  );
};

export default App;

// ─── 添加块分组菜单（全部33种块类型，按类别排列） ─────────
const BLOCK_GROUPS: { label: string; types: string[] }[] = [
  { label: '角色类', types: ['CHARACTER', 'PERSONALITY', 'GROWTH', 'BACKSTORY', 'CURRENT_STATE', 'INFORMATION_BOUNDARY', 'OMNISCIENT_LAYER'] },
  { label: '世界类', types: ['WORLDVIEW', 'FACTION', 'RULE_CONSTRAINT', 'WORLD_DEVELOPMENT', 'TIMESTAMP'] },
  { label: '叙事结构类', types: ['TIMELINE', 'SCENE', 'EVENT', 'GOAL', 'CONFLICT', 'TURNING_POINT', 'HOOK', 'FORESHADOW', 'SURPRISE'] },
  { label: '关系类', types: ['RELATIONSHIP', 'FACTION_RELATION'] },
  { label: '表达类', types: ['ATMOSPHERE', 'EMOTION_TARGET', 'RHYTHM', 'THEME_STATEMENT', 'LENS'] },
  { label: '剧本类', types: ['SCENE_HEADING', 'ACTION_LINE', 'DIALOGUE', 'VISUAL_MOTIF'] },
  { label: '大纲类', types: ['STORY_OUTLINE', 'STORY_SYNOPSIS', 'CHAPTER_OUTLINE', 'CHAPTER_DETAIL'] },
  { label: '特殊类', types: ['READER_EMOTION_CURVE', 'STORY_CARD'] },
];

const AddBlockMenu: React.FC<{ onAdd: (type: string) => void }> = ({ onAdd }) => {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    setTimeout(() => document.addEventListener('click', handleClick), 0);
    return () => document.removeEventListener('click', handleClick);
  }, [open]);

  return (
    <div ref={menuRef} style={{ position: 'absolute', top: 100, right: 12, zIndex: 10 }}>
      <button
        className="btn btn-primary"
        style={{ width: 36, height: 36, borderRadius: '50%', fontSize: 20, padding: 0, boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }}
        onClick={() => setOpen(!open)}
        title="添加块"
      >
        +
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: 42, right: 0,
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 10,
          padding: 12,
          width: 340,
          maxHeight: 440,
          overflowY: 'auto',
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
        }}>
          {BLOCK_GROUPS.map((group) => (
            <div key={group.label} style={{ marginBottom: 10 }}>
              <div style={{
                fontSize: 11, fontWeight: 700, color: '#888',
                marginBottom: 4, paddingLeft: 6,
                borderLeft: '3px solid #555',
              }}>
                {group.label}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {group.types.map((type) => (
                  <button
                    key={type}
                    className="btn btn-sm"
                    style={{
                      fontSize: 12,
                      padding: '4px 10px',
                      textAlign: 'left',
                      borderLeft: `3px solid ${BLOCK_COLORS[type] || '#999'}`,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                    }}
                    onClick={() => { onAdd(type); setOpen(false); }}
                  >
                    <span style={{ fontSize: 14, opacity: 0.7 }}>
                      {type === 'CHARACTER' ? '👤' : type === 'SCENE' ? '🎬' : type === 'GOAL' ? '🎯' : type === 'CONFLICT' ? '⚔️' : type === 'HOOK' ? '❓' : type === 'WORLDVIEW' ? '🌍' : type === 'FACTION' ? '🏛️' : type === 'TIMELINE' ? '⏱️' : type === 'EVENT' ? '📌' : type === 'TURNING_POINT' ? '💥' : type === 'FORESHADOW' ? '🔮' : type === 'SURPRISE' ? '😲' : type === 'RELATIONSHIP' ? '💞' : type === 'GROWTH' ? '🌱' : type === 'DIALOGUE' ? '💬' : '▫'}
                    </span>
                    <span>{BLOCK_LABELS[type] || type}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
