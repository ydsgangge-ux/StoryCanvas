import React, { useState } from 'react';
import { useProjectStore } from '../store/projectStore';
import { useUIStore } from '../store/uiStore'
import { useT } from '../i18n/useT';;
import { BLOCK_LABELS } from '../types/blocks';

type ImportTab = 'text' | 'json' | 'dramatica';

const JSON_TEMPLATE = {
  title: '我的小说',
  logline: '一句话概括你的故事',
  characters: [
    { name: '主角名', role: '主角', want: '外在目标', need: '内在渴望', description: '简要描述' },
    { name: '配角名', role: '配角', want: '目标', need: '渴望', description: '描述' },
    { name: '反派名', role: '反派', want: '目标', need: '渴望', description: '描述' },
  ],
  world: {
    name: '世界观名称',
    rules: ['核心规则1', '核心规则2'],
    factions: [
      { name: '势力A', ideology: '理念' },
      { name: '势力B', ideology: '理念' },
    ],
  },
  events: [
    { title: '关键事件1', description: '发生了什么', chapter: 1 },
    { title: '关键事件2', description: '发生了什么', chapter: 5 },
  ],
};

const ImportDialog: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const { currentProject, loadProjects, loadProject } = useProjectStore();
  const { showToast } = useUIStore();
  const [tab, setTab] = useState<ImportTab>('text');

  // 文本提取
  const [rawText, setRawText] = useState('');
  const [extracting, setExtracting] = useState(false);
  const [extractionResult, setExtractionResult] = useState<any>(null);

  // 结构化JSON
  const [jsonInput, setJsonInput] = useState('');
  const [importingJson, setImportingJson] = useState(false);

  // Dramatica-Flow
  const [dfFile, setDfFile] = useState<File | null>(null);
  const [importingDf, setImportingDf] = useState(false);

  const handleExtract = async () => {
    if (!currentProject || !rawText.trim()) return;
    setExtracting(true);
    setExtractionResult(null);
    try {
      const res = await fetch(`/api/projects/${currentProject.id}/extract-from-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: rawText }),
      });
      if (!res.ok) { showToast('提取失败', 'error'); return; }
      const data = await res.json();
      setExtractionResult(data.extraction || data);
      showToast(`提取完成: ${data.characters_extracted}个角色`);
    } catch { showToast('提取请求失败', 'error'); }
    setExtracting(false);
  };

  const handleImportExtraction = async () => {
    if (!currentProject || !extractionResult) return;
    try {
      const res = await fetch(`/api/projects/${currentProject.id}/import/structured`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(extractionResult),
      });
      if (!res.ok) { showToast('导入失败', 'error'); return; }
      const data = await res.json();
      showToast(`导入完成: 画布${data.on_canvas}个·池${data.in_pool}个`);
      await loadProject(currentProject.id);
      onClose();
    } catch { showToast('导入请求失败', 'error'); }
  };

  const handleImportJson = async () => {
    if (!currentProject || !jsonInput.trim()) return;
    setImportingJson(true);
    try {
      const parsed = JSON.parse(jsonInput);
      const res = await fetch(`/api/projects/${currentProject.id}/import/structured`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed),
      });
      if (!res.ok) { showToast('导入失败', 'error'); return; }
      const data = await res.json();
      showToast(`导入完成: 画布${data.on_canvas}个·池${data.in_pool}个`);
      await loadProject(currentProject.id);
      onClose();
    } catch (e: any) { showToast(e.message || 'JSON格式错误', 'error'); }
    setImportingJson(false);
  };

  const handleImportDramatica = async () => {
    if (!dfFile) return;
    setImportingDf(true);
    try {
      const form = new FormData();
      form.append('file', dfFile);
      const res = await fetch('/api/import/dramatica-flow', { method: 'POST', body: form });
      if (!res.ok) { showToast('导入失败', 'error'); return; }
      const data = await res.json();
      showToast(`导入完成: ${data.title} (画布${data.on_canvas}个·池${data.in_pool}个)`);
      await loadProjects();
      await loadProject(data.project_id);
      onClose();
    } catch { showToast('导入请求失败', 'error'); }
    setImportingDf(false);
  };

  const tabs: { key: ImportTab; label: string; icon: string }[] = [
    { key: 'text', label: '从文本提取', icon: '📝' },
    { key: 'json', label: '结构化JSON', icon: '📋' },
    { key: 'dramatica', label: 'Dramatica-Flow', icon: '📦' },
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ width: 600, maxHeight: '80vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <h2 style={{ marginBottom: 12 }}>📥 导入</h2>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 12, borderBottom: '1px solid var(--border-color)' }}>
          {tabs.map(t => (
            <button key={t.key} className={`btn btn-sm ${tab === t.key ? 'btn-primary' : ''}`}
              style={{ borderRadius: '6px 6px 0 0', padding: '6px 14px' }}
              onClick={() => setTab(t.key)}>{t.icon} {t.label}</button>
          ))}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: '0 4px' }}>

          {/* TAB 1: 文本提取 */}
          {tab === 'text' && (
            <div>
              <label className="form-label">粘贴小说正文（支持多章）</label>
              <textarea className="form-textarea" rows={10}
                value={rawText} onChange={(e) => setRawText(e.target.value)}
                placeholder="粘贴你的小说正文...&#10;系统会自动按「第N章」分章，然后用AI提取角色/世界观/事件" />
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button className="btn btn-primary" onClick={handleExtract} disabled={extracting || !rawText.trim()}>
                  {extracting ? '提取中...' : '🔍 LLM提取结构化数据'}
                </button>
              </div>

              {/* 提取预览 */}
              {extractionResult && (
                <div style={{ marginTop: 12, padding: 12, background: 'var(--bg-card)', borderRadius: 8 }}>
                  <h3 style={{ fontSize: 15, marginBottom: 8 }}>{extractionResult.title || '提取结果'}</h3>
                  {extractionResult.logline && <div style={{ fontSize: 12, color: '#aaa', marginBottom: 8 }}>{extractionResult.logline}</div>}

                  <div style={{ fontSize: 12, marginBottom: 8 }}>
                    <span style={{ color: '#4A90D9' }}>角色 {extractionResult.characters?.length || 0}个</span>
                    <span style={{ margin: '0 8px', color: '#666' }}>·</span>
                    <span style={{ color: '#50C878' }}>世界 {extractionResult.world?.name ? '✓' : '✗'}</span>
                    <span style={{ margin: '0 8px', color: '#666' }}>·</span>
                    <span style={{ color: '#F39C12' }}>事件 {extractionResult.events?.length || 0}个</span>
                  </div>

                  {/* 角色列表 */}
                  {extractionResult.characters?.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#888', marginBottom: 4 }}>角色</div>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {extractionResult.characters.map((c: any, i: number) => (
                          <span key={i} style={{
                            fontSize: 11, padding: '2px 8px', borderRadius: 4,
                            background: c.role === '主角' ? 'rgba(74,144,217,0.2)' : 'rgba(100,100,100,0.2)',
                            color: c.role === '主角' ? '#4A90D9' : '#aaa',
                          }}>{c.name}{c.role === '主角' ? ' ★' : ''}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  <button className="btn btn-primary" onClick={handleImportExtraction}
                    style={{ marginTop: 8, width: '100%' }}>
                    ✅ 确认导入
                  </button>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: 结构化JSON */}
          {tab === 'json' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <label className="form-label" style={{ margin: 0 }}>粘贴结构化JSON</label>
                <button className="btn btn-sm btn-ghost" style={{ fontSize: 11 }}
                  onClick={() => setJsonInput(JSON.stringify(JSON_TEMPLATE, null, 2))}>
                  📋 填入模板
                </button>
              </div>
              <textarea className="form-textarea" rows={14}
                value={jsonInput} onChange={(e) => setJsonInput(e.target.value)}
                placeholder={'{\n  "characters": [...],\n  "world": {...},\n  "events": [...]\n}'} />
              <div style={{ fontSize: 11, color: '#888', margin: '4px 0 8px' }}>
                💡 点击「填入模板」查看格式。支持任意 JSON，主角自动放画布，配角/事件进块池。
                {currentProject && <span> 导入到当前项目「{currentProject.title}」。</span>}
              </div>
              <button className="btn btn-primary" onClick={handleImportJson} disabled={importingJson || !jsonInput.trim()}
                style={{ width: '100%' }}>
                {importingJson ? '导入中...' : currentProject ? '📥 导入到当前项目' : '📥 导入（新建项目）'}
              </button>
            </div>
          )}

          {/* TAB 3: Dramatica-Flow */}
          {tab === 'dramatica' && (
            <div>
              <label className="form-label">上传 Dramatica-Flow 项目文件</label>
              <div style={{
                border: '2px dashed var(--border-color)', borderRadius: 8, padding: 30,
                textAlign: 'center', cursor: 'pointer', marginBottom: 8,
                background: dfFile ? 'rgba(74,144,217,0.1)' : 'transparent',
              }} onClick={() => document.getElementById('df-file-input')?.click()}>
                {dfFile ? (
                  <div>
                    <div style={{ fontSize: 32, marginBottom: 8 }}>📦</div>
                    <div style={{ fontWeight: 600 }}>{dfFile.name}</div>
                    <div style={{ fontSize: 12, color: '#888' }}>{(dfFile.size / 1024).toFixed(1)} KB</div>
                  </div>
                ) : (
                  <div>
                    <div style={{ fontSize: 32, marginBottom: 8 }}>📂</div>
                    <div style={{ color: '#888' }}>点击选择 .zip 文件</div>
                    <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>支持 Dramatica-Flow 项目导出的 zip</div>
                  </div>
                )}
              </div>
              <input id="df-file-input" type="file" accept=".zip" style={{ display: 'none' }}
                onChange={(e) => setDfFile(e.target.files?.[0] || null)} />
              <button className="btn btn-primary" onClick={handleImportDramatica} disabled={importingDf || !dfFile}
                style={{ width: '100%' }}>
                {importingDf ? '导入中...' : '📥 导入 Dramatica-Flow 项目'}
              </button>
            </div>
          )}
        </div>

        <button className="btn" onClick={onClose} style={{ marginTop: 12 }}>关闭</button>
      </div>
    </div>
  );
};

export default ImportDialog;
