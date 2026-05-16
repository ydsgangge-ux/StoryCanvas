import React, { useState } from 'react';
import { useProjectStore } from '../store/projectStore';
import { useUIStore } from '../store/uiStore';
import { useT } from '../i18n/useT';
import { t } from '../i18n';

type ImportTab = 'text' | 'json' | 'dramatica';

const JSON_TEMPLATE = {
  title: t('import.template_title'),
  logline: t('import.template_logline'),
  characters: [
    { name: t('import.template_protagonist_name'), role: '主角', want: t('import.template_protagonist_want'), need: t('import.template_protagonist_need'), description: t('import.template_protagonist_desc') },
    { name: t('import.template_supporting_name'), role: '配角', want: t('import.template_goal'), need: t('import.template_desire'), description: t('import.template_desc') },
    { name: t('import.template_antagonist_name'), role: '反派', want: t('import.template_goal'), need: t('import.template_desire'), description: t('import.template_desc') },
  ],
  world: {
    name: t('import.template_world_name'),
    rules: [t('import.template_rule', { n: 1 }), t('import.template_rule', { n: 2 })],
    factions: [
      { name: t('import.template_faction', { n: 'A' }), ideology: t('import.template_ideology') },
      { name: t('import.template_faction', { n: 'B' }), ideology: t('import.template_ideology') },
    ],
  },
  events: [
    { title: t('import.template_event', { n: 1 }), description: t('import.template_event_desc'), chapter: 1 },
    { title: t('import.template_event', { n: 2 }), description: t('import.template_event_desc'), chapter: 5 },
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
      if (!res.ok) { showToast(t('import.extract_failed'), 'error'); return; }
      const data = await res.json();
      setExtractionResult(data.extraction || data);
      showToast(t('import.extract_complete', { count: data.characters_extracted }));
    } catch { showToast(t('import.import_request_failed'), 'error'); }
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
      if (!res.ok) { showToast(t('import.import_failed'), 'error'); return; }
      const data = await res.json();
      showToast(t('import.import_complete', { canvas: data.on_canvas, pool: data.in_pool }));
      await loadProject(currentProject.id);
      onClose();
    } catch { showToast(t('import.import_request_failed'), 'error'); }
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
      if (!res.ok) { showToast(t('import.import_failed'), 'error'); return; }
      const data = await res.json();
      showToast(t('import.import_complete', { canvas: data.on_canvas, pool: data.in_pool }));
      await loadProject(currentProject.id);
      onClose();
    } catch (e: any) { showToast(e.message || t('import.json_format_error'), 'error'); }
    setImportingJson(false);
  };

  const handleImportDramatica = async () => {
    if (!dfFile) return;
    setImportingDf(true);
    try {
      const form = new FormData();
      form.append('file', dfFile);
      const isStorycanvas = dfFile.name.endsWith('.storycanvas');
      const endpoint = isStorycanvas ? '/api/projects/import' : '/api/import/dramatica-flow';
      const res = await fetch(endpoint, { method: 'POST', body: form });
      if (!res.ok) {
        const errText = await res.text();
        try { const errJson = JSON.parse(errText); showToast(errJson.detail || t('import.import_failed'), 'error'); }
        catch { showToast(t('import.import_failed'), 'error'); }
        return;
      }
      const data = await res.json();
      showToast(t('import.import_complete', { canvas: data.on_canvas ?? data.stats?.blocks ?? 0, pool: data.in_pool ?? 0 }));
      await loadProjects();
      await loadProject(data.project_id);
      onClose();
    } catch { showToast(t('import.import_request_failed'), 'error'); }
    setImportingDf(false);
  };

  const tabs: { key: ImportTab; labelKey: string; icon: string }[] = [
    { key: 'text', labelKey: 'import.text_tab', icon: '📝' },
    { key: 'json', labelKey: 'import.json_tab', icon: '📋' },
    { key: 'dramatica', labelKey: 'import.dramatica_tab', icon: '📦' },
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ width: 600, maxHeight: '80vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <h2 style={{ marginBottom: 12 }}>📥 {t('import.title')}</h2>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 12, borderBottom: '1px solid var(--border-color)' }}>
          {tabs.map(tabItem => (
            <button key={tabItem.key} className={`btn btn-sm ${tab === tabItem.key ? 'btn-primary' : ''}`}
              style={{ borderRadius: '6px 6px 0 0', padding: '6px 14px' }}
              onClick={() => setTab(tabItem.key)}>{tabItem.icon} {t(tabItem.labelKey)}</button>
          ))}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: '0 4px' }}>

          {/* TAB 1: 文本提取 */}
          {tab === 'text' && (
            <div>
              <label className="form-label">{t('import.paste_novel')}</label>
              <textarea className="form-textarea" rows={10}
                value={rawText} onChange={(e) => setRawText(e.target.value)}
                placeholder={t('import.text_placeholder')} />
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button className="btn btn-primary" onClick={handleExtract} disabled={extracting || !rawText.trim()}>
                  {extracting ? t('import.extracting') : `🔍 ${t('import.extract')}`}
                </button>
              </div>

              {/* 提取预览 */}
              {extractionResult && (
                <div style={{ marginTop: 12, padding: 12, background: 'var(--bg-card)', borderRadius: 8 }}>
                  <h3 style={{ fontSize: 15, marginBottom: 8 }}>{extractionResult.title || t('import.extraction_result')}</h3>
                  {extractionResult.logline && <div style={{ fontSize: 12, color: '#aaa', marginBottom: 8 }}>{extractionResult.logline}</div>}

                  <div style={{ fontSize: 12, marginBottom: 8 }}>
                    <span style={{ color: '#4A90D9' }}>{t('import.characters_label')} {extractionResult.characters?.length || 0}</span>
                    <span style={{ margin: '0 8px', color: '#666' }}>·</span>
                    <span style={{ color: '#50C878' }}>{t('import.world_label')} {extractionResult.world?.name ? '✓' : '✗'}</span>
                    <span style={{ margin: '0 8px', color: '#666' }}>·</span>
                    <span style={{ color: '#F39C12' }}>{t('import.events_label')} {extractionResult.events?.length || 0}</span>
                  </div>

                  {/* 角色列表 */}
                  {extractionResult.characters?.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#888', marginBottom: 4 }}>{t('import.characters_label')}</div>
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
                    ✅ {t('import.confirm_import')}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: 结构化JSON */}
          {tab === 'json' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <label className="form-label" style={{ margin: 0 }}>{t('import.paste_json_label')}</label>
                <button className="btn btn-sm btn-ghost" style={{ fontSize: 11 }}
                  onClick={() => setJsonInput(JSON.stringify(JSON_TEMPLATE, null, 2))}>
                  📋 {t('import.json_template_btn')}
                </button>
              </div>
              <textarea className="form-textarea" rows={14}
                value={jsonInput} onChange={(e) => setJsonInput(e.target.value)}
                placeholder={'{\n  "characters": [...],\n  "world": {...},\n  "events": [...]\n}'} />
              <div style={{ fontSize: 11, color: '#888', margin: '4px 0 8px' }}>
                💡 {t('import.json_hint')}
                {currentProject && <span> {t('import.import_to_current', { title: currentProject.title })}</span>}
              </div>
              <button className="btn btn-primary" onClick={handleImportJson} disabled={importingJson || !jsonInput.trim()}
                style={{ width: '100%' }}>
                {importingJson ? t('import.importing') : currentProject ? `📥 ${t('import.import_to_current')}` : `📥 ${t('import.import_new_project')}`}
              </button>
            </div>
          )}

          {/* TAB 3: Dramatica-Flow */}
          {tab === 'dramatica' && (
            <div>
              <label className="form-label">{t('import.dramatica_upload')}</label>
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
                    <div style={{ color: '#888' }}>{t('import.click_select_zip')}</div>
                    <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>{t('import.dramatica_hint')}</div>
                  </div>
                )}
              </div>
              <input id="df-file-input" type="file" accept=".zip,.storycanvas" style={{ display: 'none' }}
                onChange={(e) => setDfFile(e.target.files?.[0] || null)} />
              <button className="btn btn-primary" onClick={handleImportDramatica} disabled={importingDf || !dfFile}
                style={{ width: '100%' }}>
                {importingDf ? t('import.importing') : `📥 ${t('import.dramatica_import')}`}
              </button>
            </div>
          )}
        </div>

        <button className="btn" onClick={onClose} style={{ marginTop: 12 }}>{t('common.close')}</button>
      </div>
    </div>
  );
};

export default ImportDialog;
