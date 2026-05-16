import React, { useState, useEffect, useRef } from 'react';
import { useProjectStore } from '../store/projectStore';
import { useUIStore } from '../store/uiStore';
import { generateOutline, generateChapterContent } from '../api/generate';
import { useT } from '../i18n/useT';

interface OutlineBlock {
  id: string;
  type: 'CHAPTER_OUTLINE' | 'CHAPTER_DETAIL';
  chapter_number: number;
  title: string;
  summary: string;
  status: string;
}

interface AuditIssue {
  dimension: string;
  severity: string;
  description: string;
  location: string;
  suggestion: string;
}

interface ExtractedForeshadow {
  title: string;
  type: string;
  description: string;
  location: string;
  urgency: string;
  suggested_payoff_chapter: string | number;
}

interface AuditResult {
  passed: boolean;
  issues: AuditIssue[];
  critical_count: number;
  total_issues: number;
  overall_note?: string;
  foreshadows_extracted?: ExtractedForeshadow[];
}

const PROSE_STYLE_KEYS = ['style.standard', 'style.ornate', 'style.plain', 'style.humorous', 'style.austere', 'style.poetic', 'style.concise'];
const POV_OPTION_KEYS = ['', 'pov.multi', 'pov.limited_third', 'pov.omniscient', 'pov.first_person', 'pov.ensemble'];
const DENSITY_OPTION_KEYS = ['', 'density.epic', 'density.minimalist', 'density.standard', 'density.stream', 'density.prose_poetry'];
const TONE_OPTION_KEYS = ['tone.austere_restrained', 'tone.moral_gray', 'tone.passionate'];

const WritingPanel: React.FC = () => {
  const { t } = useT();
  const { currentProject, loadProject } = useProjectStore();
  const { showToast } = useUIStore();

  const [outlineBlocks, setOutlineBlocks] = useState<OutlineBlock[]>([]);
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [chapterNum, setChapterNum] = useState(1);
  const [additionalInstructions, setAdditionalInstructions] = useState('');
  const [output, setOutput] = useState('');
  const [stage, setStage] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [mode, setMode] = useState<'outline' | 'content' | 'audit'>('outline');
  const [auditResult, setAuditResult] = useState<AuditResult | null>(null);
  const [isAuditing, setIsAuditing] = useState(false);
  const [isRevising, setIsRevising] = useState(false);

  // Rewrite state
  const [rewriteInstruction, setRewriteInstruction] = useState('');
  const [isRewriting, setIsRewriting] = useState(false);
  const outputRef = useRef<HTMLTextAreaElement>(null);

  // ─── 风格设置 ─────────────────────────────────
  const [proseStyle, setProseStyle] = useState('');
  const [narrativePov, setNarrativePov] = useState('');
  const [languageDensity, setLanguageDensity] = useState('');
  const [tone, setTone] = useState<string[]>([]);
  const [customInstructions, setCustomInstructions] = useState('');
  const [isStyleExpanded, setIsStyleExpanded] = useState(false);

  useEffect(() => {
    if (!currentProject) return;
    const { blocks } = useProjectStore.getState();
    const filtered = blocks
      .filter((b: any) => b.type === 'CHAPTER_OUTLINE' || b.type === 'CHAPTER_DETAIL')
      .map((b: any) => ({
        id: b.id,
        type: b.type as 'CHAPTER_OUTLINE' | 'CHAPTER_DETAIL',
        chapter_number: (b.content as any)?.chapter_number || 0,
        title: (b.content as any)?.title || '',
        summary: (b.content as any)?.summary || (b.content as any)?.key_conflicts || '',
        status: (b.content as any)?.status || 'planned',
      }))
      .sort((a: OutlineBlock, b: OutlineBlock) => a.chapter_number - b.chapter_number);
    setOutlineBlocks(filtered);
    if (filtered.length > 0 && !selectedBlockId) {
      setSelectedBlockId(filtered[0].id);
      setChapterNum(filtered[0].chapter_number);
    }
  }, [currentProject, currentProject?.id]);

  useEffect(() => {
    const block = outlineBlocks.find((b) => b.id === selectedBlockId);
    if (block) setChapterNum(block.chapter_number);
  }, [selectedBlockId]);

  // 切换章节时自动加载已有正文
  useEffect(() => {
    if (!currentProject) return;
    const loadContent = async () => {
      try {
        const res = await fetch(`/api/projects/${currentProject.id}/chapters/${chapterNum}`);
        if (res.ok) {
          const data = await res.json();
          if (data.exists && data.content) {
            setOutput(data.content);
          } else if (!data.exists && output !== '') {
            // 该章还没有正文，但不清空当前已生成的内容
          }
        }
      } catch {}
    };
    // 不在生成过程中才加载已有内容
    if (!isGenerating) loadContent();
  }, [currentProject?.id, chapterNum, isGenerating]);

  useEffect(() => {
    if (!currentProject || mode !== 'audit') return;
    const loadSavedAudit = async () => {
      try {
        const res = await fetch(`/api/projects/${currentProject.id}/audit/${chapterNum}`);
        if (res.ok) {
          const data = await res.json();
          if (data.audit) {
            const audit = data.audit;
            setAuditResult({
              passed: audit.passed,
              issues: audit.issues || [],
              critical_count: audit.critical_count || 0,
              total_issues: audit.total_issues || 0,
              overall_note: audit.parsed?.overall_note || audit.overall_note || '',
              foreshadows_extracted: audit.foreshadows_extracted || [],
            });
          }
        }
      } catch {}
    };
    loadSavedAudit();
  }, [currentProject?.id, chapterNum, mode]);

  const selectedBlock = outlineBlocks.find((b) => b.id === selectedBlockId);

  const handleGenerateOutline = async () => {
    if (!currentProject) return;
    setIsGenerating(true);
    setOutput('');
    setStage(t('writing.generating_outline'));
    await generateOutline(
      currentProject.id, chapterNum, additionalInstructions,
      (text) => setOutput((prev) => prev + text),
      () => { setStage(null); setIsGenerating(false); showToast(t('writing.outline_complete')); loadProject(currentProject.id); },
      (err) => { setStage(null); setIsGenerating(false); showToast(err, 'error'); }
    );
  };

  const handleGenerateContent = async () => {
    if (!currentProject) return;
    setIsGenerating(true);
    setOutput('');
    setStage(t('writing.collecting_blocks'));
    let fullContent = '';
    const detailBlock = selectedBlock?.type === 'CHAPTER_DETAIL' ? selectedBlock.id : undefined;
    await generateChapterContent(
      currentProject.id, chapterNum, true,
      (s, msg) => setStage(msg),
      (text) => { fullContent += text; setOutput(fullContent); },
      (result) => {
        setStage(null); setIsGenerating(false);
        showToast(t('writing.chapter_generated', { num: chapterNum, count: result.word_count }));
        loadProject(currentProject.id);
      },
      (err) => { setStage(null); setIsGenerating(false); showToast(err, 'error'); },
      (violations) => showToast(t('writing.info_boundary_warning', { count: violations.length }), 'warning'),
      detailBlock
    );
  };

  const handleAudit = async () => {
    if (!currentProject) return;
    setIsAuditing(true);
    setAuditResult(null);
    showToast(t('writing.auditing_status'));
    try {
      const res = await fetch(`/api/projects/${currentProject.id}/audit/${chapterNum}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        const audit = data.audit || data;
        setAuditResult({
          passed: audit.passed,
          issues: audit.issues || [],
          critical_count: audit.critical_count || 0,
          total_issues: audit.total_issues || 0,
          overall_note: audit.parsed?.overall_note || '',
          foreshadows_extracted: audit.foreshadows_extracted || [],
        });
        showToast(audit.passed ? t('writing.audit_passed') : t('writing.audit_failed', { count: audit.critical_count }), audit.passed ? 'info' : 'warning');
      }
    } catch {
      showToast(t('writing.audit_request_failed'), 'error');
    }
    setIsAuditing(false);
  };

  const handleReviseAll = async () => {
    if (!currentProject) return;
    setIsRevising(true);
    showToast(t('writing.revising_all'));
    try {
      const res = await fetch(`/api/projects/${currentProject.id}/revise/${chapterNum}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.revised_content) {
          setOutput(data.revised_content);
          setAuditResult(null);
          showToast(t('writing.revise_all_complete'));
          loadProject(currentProject.id);
        } else {
          showToast(data.message || t('writing.no_revision_needed'));
        }
      } else {
        showToast(t('writing.revise_failed'), 'error');
      }
    } catch {
      showToast(t('writing.revise_error'), 'error');
    }
    setIsRevising(false);
  };

  const handleCreateForeshadowBlock = async (fs: ExtractedForeshadow) => {
    if (!currentProject) return;
    const blockType = fs.type === 'hook' ? 'HOOK' : 'FORESHADOW';
    const payoff = fs.suggested_payoff_chapter ? Number(fs.suggested_payoff_chapter) : '';
    try {
      await useProjectStore.getState().addBlock(currentProject.id, {
        type: blockType,
        canvas_x: 200 + Math.random() * 300,
        canvas_y: 200 + Math.random() * 200,
        content: {
          title: fs.title,
          description: fs.description,
          hint_content: fs.location,
          urgency: fs.urgency,
          status: 'planted',
          plant_chapter: chapterNum,
          payoff_chapter: payoff || '',
        },
      });
      showToast(t('writing.foreshadow_block_created', { title: fs.title }));
    } catch {
      showToast(t('writing.foreshadow_block_failed'), 'error');
    }
  };

  const handleCreateAllForeshadows = async () => {
    if (!currentProject || !auditResult?.foreshadows_extracted?.length) return;
    for (const fs of auditResult.foreshadows_extracted) {
      await handleCreateForeshadowBlock(fs);
    }
    showToast(t('writing.all_foreshadows_created', { count: auditResult.foreshadows_extracted.length }));
  };

  /** AI改写正文（支持选中部分 + 上下文定点修改） */
  const handleRewrite = async (issue?: AuditIssue) => {
    if (!currentProject || !output.trim()) return;
    setIsRewriting(true);
    showToast(t('writing.rewriting'));
    try {
      // 获取选中文本及上下文
      let selectedText = '';
      let contextBefore = '';
      let contextAfter = '';
      if (outputRef.current) {
        const ta = outputRef.current;
        const start = ta.selectionStart;
        const end = ta.selectionEnd;
        if (start !== end) {
          selectedText = output.substring(start, end);
          // 取选中文本前后各 200 字作为上下文
          contextBefore = output.substring(Math.max(0, start - 200), start);
          contextAfter = output.substring(end, Math.min(output.length, end + 200));
        }
      }

      const body: any = { chapter_num: chapterNum, instruction: rewriteInstruction || t('writing.rewrite_placeholder') };
      if (selectedText) {
        body.selected_text = selectedText;
        body.context_before = contextBefore;
        body.context_after = contextAfter;
      }
      if (issue) {
        body.issue = `${issue.dimension}: ${issue.description}`;
        if (issue.suggestion) body.instruction = issue.suggestion;
      }
      const res = await fetch(`/api/projects/${currentProject.id}/generate/rewrite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.is_segment && selectedText) {
          // 段落级修改：用改写后的段落替换原文中选中的部分
          const idx = output.indexOf(selectedText);
          if (idx !== -1) {
            setOutput(output.substring(0, idx) + data.revised_content + output.substring(idx + selectedText.length));
          } else {
            setOutput(data.revised_content);
          }
        } else {
          // 全文改写：直接替换全部内容
          setOutput(data.revised_content);
        }
        showToast(selectedText ? t('writing.segment_revised') : t('writing.rewrite_complete'));
      } else {
        showToast(t('writing.rewrite_failed'), 'error');
      }
    } catch {
      showToast(t('writing.rewrite_error'), 'error');
    }
    setIsRewriting(false);
  };

  /** 保存正文到 chapters 表 */
  const handleSaveContent = async () => {
    if (!currentProject || !output.trim()) return;
    try {
      const res = await fetch(`/api/projects/${currentProject.id}/generate/chapter-content`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chapter_num: chapterNum, outline_confirmed: true, save_only: true, content: output }),
      });
      if (res.ok) {
        showToast(t('writing.content_saved'));
        loadProject(currentProject.id);
      } else {
        showToast(t('writing.save_failed'), 'error');
      }
    } catch {
      showToast(t('writing.save_error'), 'error');
    }
  };

  const handleSaveStyle = async () => {
    if (!currentProject) return;
    try {
      const res = await fetch(`/api/projects/${currentProject.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          style_sig: JSON.stringify({
            prose_style: proseStyle || undefined,
            narrative_pov: narrativePov || undefined,
            language_density: languageDensity || undefined,
            tone: tone.length > 0 ? tone : undefined,
            custom_instructions: customInstructions || undefined,
          }),
        }),
      });
      if (res.ok) {
        showToast(t('writing.style_saved'));
      } else {
        showToast(t('writing.save_failed'), 'error');
      }
    } catch {
      showToast(t('writing.save_error'), 'error');
    }
  };

  const toggleTone = (t: string) => {
    setTone((prev) => prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]);
  };

  return (
    <div className="panel" style={{ width: '50%', minWidth: 420 }}>
      <div className="panel-header">
        <span>{t('writing.title')}</span>
        <div style={{ display: 'flex', gap: 4 }}>
          <button className={`btn btn-sm ${mode === 'outline' ? 'btn-primary' : ''}`} onClick={() => setMode('outline')}>{t('writing.outline')}</button>
          <button className={`btn btn-sm ${mode === 'content' ? 'btn-primary' : ''}`} onClick={() => setMode('content')}>{t('writing.content')}</button>
          <button className={`btn btn-sm ${mode === 'audit' ? 'btn-primary' : ''}`} onClick={() => setMode('audit')}>{t('writing.audit')}</button>
        </div>
      </div>
      <div className="panel-body">
        <div className="writing-panel">

          {/* ─── 章节块选择器 ─────────────────── */}
          <div style={{ marginBottom: 12 }}>
            <label className="form-label">{t('writing.select_chapter_block')}</label>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
              {outlineBlocks.length === 0 ? (
                <span style={{ fontSize: 12, color: '#6c6c80' }}>
                  {t('writing.no_chapter_blocks')}
                </span>
              ) : (
                outlineBlocks.map((ob) => (
                  <button key={ob.id} className={`btn btn-sm ${selectedBlockId === ob.id ? 'btn-primary' : ''}`}
                    style={{ fontSize: 11, borderLeft: `3px solid ${ob.type === 'CHAPTER_DETAIL' ? '#50C878' : '#4A90D9'}` }}
                    onClick={() => { setSelectedBlockId(ob.id); setChapterNum(ob.chapter_number); }}
                    title={ob.type === 'CHAPTER_DETAIL' ? t('writing.chapter_detail') : t('writing.chapter_outline_type')}>
                    {ob.type === 'CHAPTER_DETAIL' ? '📄' : '📋'} {t('writing.chapter')}{ob.chapter_number} {ob.title?.substring(0, 8) || ''}
                  </button>
                ))
              )}
            </div>
            {selectedBlock && (
              <div style={{ fontSize: 11, color: '#a0a0b0', marginTop: 4, padding: '4px 8px', background: 'var(--bg-card)', borderRadius: 4,
                borderLeft: `3px solid ${selectedBlock.type === 'CHAPTER_DETAIL' ? '#50C878' : '#4A90D9'}` }}>
                <span style={{ color: selectedBlock.type === 'CHAPTER_DETAIL' ? '#50C878' : '#4A90D9', fontWeight: 600 }}>
                  {selectedBlock.type === 'CHAPTER_DETAIL' ? t('writing.chapter_detail') : t('writing.chapter_outline_type')}
                </span>: {selectedBlock.summary?.substring(0, 120) || t('writing.no_summary')}
                {selectedBlock.type === 'CHAPTER_OUTLINE' && mode === 'content' && (
                  <span style={{ color: '#F39C12' }}> （{t('writing.suggest_detail')}）</span>
                )}
              </div>
            )}
          </div>

          {/* ─── 章节号 ─────────────────────────── */}
          <div className="chapter-selector" style={{ marginBottom: 8 }}>
            <label className="form-label" style={{ margin: 0 }}>{t('writing.chapter_number')}:</label>
            <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <button className="btn btn-sm btn-ghost" onClick={() => setChapterNum(Math.max(1, chapterNum - 1))}>←</button>
              <input className="form-input" type="number" value={chapterNum}
                onChange={(e) => setChapterNum(Math.max(1, parseInt(e.target.value) || 1))}
                min={1} style={{ width: 60, textAlign: 'center' }} />
              <button className="btn btn-sm btn-ghost" onClick={() => setChapterNum(chapterNum + 1)}>→</button>
            </div>
          </div>

          {/* ─── 额外指令 ───────────────────────── */}
          {mode !== 'audit' && (
            <div className="form-group">
              <label className="form-label">{t('writing.extra_instructions')}</label>
              <textarea className="form-textarea" rows={2} value={additionalInstructions}
                onChange={(e) => setAdditionalInstructions(e.target.value)}
                placeholder={t('writing.extra_instructions_placeholder')} disabled={isGenerating} />
            </div>
          )}

          {/* ─── 写作风格 ───────────────────────── */}
          <div style={{ marginBottom: 12, border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden' }}>
            <div style={{ padding: '8px 12px', cursor: 'pointer', fontSize: 12, fontWeight: 600,
              background: 'var(--bg-card)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
              onClick={() => setIsStyleExpanded(!isStyleExpanded)}>
              <span>🎨 {t('writing.writing_style')}</span>
              <span style={{ fontSize: 10, color: '#888' }}>{isStyleExpanded ? t('writing.collapse') + ' ▲' : t('writing.expand') + ' ▼'}</span>
            </div>
            {isStyleExpanded && (
              <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div>
                  <label className="form-label">{t('writing.prose_style')}</label>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 2 }}>
                    {PROSE_STYLE_KEYS.map((s) => (
                      <button key={s} className={`btn btn-sm ${proseStyle === s ? 'btn-primary' : ''}`}
                        onClick={() => setProseStyle(proseStyle === s ? '' : s)} style={{ fontSize: 11 }}>{t(s)}</button>
                    ))}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <div style={{ flex: 1 }}>
                    <label className="form-label">{t('writing.narrative_pov')}</label>
                    <select className="form-input" value={narrativePov}
                      onChange={(e) => setNarrativePov(e.target.value)} style={{ fontSize: 11, marginTop: 2 }}>
                      {POV_OPTION_KEYS.map((o) => <option key={o} value={o}>{o ? t(o) : t('writing.default_option')}</option>)}
                    </select>
                  </div>
                  <div style={{ flex: 1 }}>
                    <label className="form-label">{t('writing.language_density')}</label>
                    <select className="form-input" value={languageDensity}
                      onChange={(e) => setLanguageDensity(e.target.value)} style={{ fontSize: 11, marginTop: 2 }}>
                      {DENSITY_OPTION_KEYS.map((o) => <option key={o} value={o}>{o ? t(o) : t('writing.default_option')}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="form-label">{t('writing.tone_tags')}</label>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 2 }}>
                    {TONE_OPTION_KEYS.map((tk) => (
                      <button key={tk} className={`btn btn-sm ${tone.includes(tk) ? 'btn-primary' : ''}`}
                        onClick={() => toggleTone(tk)} style={{ fontSize: 11 }}>{t(tk)}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="form-label">{t('writing.custom_instructions')}</label>
                  <textarea className="form-textarea" rows={2} value={customInstructions}
                    onChange={(e) => setCustomInstructions(e.target.value)}
                    placeholder={t('writing.custom_instructions_placeholder')} style={{ fontSize: 11 }} />
                </div>
                <button className="btn btn-sm btn-primary" onClick={handleSaveStyle} style={{ alignSelf: 'flex-end' }}>{t('writing.save_style')}</button>
              </div>
            )}
          </div>

          {/* ─── 操作按钮（非审计模式） ─────────── */}
          {mode !== 'audit' && (
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary"
                onClick={mode === 'outline' ? handleGenerateOutline : handleGenerateContent}
                disabled={isGenerating || !currentProject}>
                {isGenerating ? <><span className="loading-spinner" /> {t('writing.generating')}</> : (mode === 'outline' ? t('writing.generate_outline') : t('writing.generate_content'))}
              </button>
              <button className="btn" onClick={() => { setOutput(''); setStage(null); }} disabled={isGenerating}>{t('writing.clear')}</button>
              {output && mode === 'content' && (
                <button className="btn btn-sm" onClick={handleSaveContent} style={{ color: '#50C878' }}>💾 {t('writing.save_content')}</button>
              )}
            </div>
          )}

          {/* ─── 操作按钮（审计模式） ─────────── */}
          {mode === 'audit' && (
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary" onClick={handleAudit} disabled={isAuditing || !currentProject}>
                {isAuditing ? t('writing.auditing') : '🔍 ' + t('writing.run_audit_btn')}
              </button>
              {auditResult && !auditResult.passed && (
                <button className="btn" style={{ background: 'linear-gradient(135deg, #50C878, #4A90D9)', color: '#fff', border: 'none' }}
                  onClick={handleReviseAll} disabled={isRevising || !currentProject}>
                  {isRevising ? <><span className="loading-spinner" /> {t('writing.revising_all')}</> : '🤖 ' + t('writing.revise_all_btn')}
                </button>
              )}
              <button className="btn" onClick={() => { setOutput(''); setStage(null); setAuditResult(null); }} disabled={isGenerating}>{t('writing.clear')}</button>
            </div>
          )}

          {/* ─── 进度 ─────────────────────────── */}
          {stage && (<div className="generation-stage"><span className="loading-spinner" style={{ width: 14, height: 14, marginRight: 8 }} />{stage}</div>)}

          {/* ─── 可编辑的正文/细纲输出 ─────────── */}
          {mode !== 'audit' && (
            <>
              <textarea ref={outputRef} className="form-textarea generation-output"
                style={{ flex: 1, minHeight: 200, whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.7 }}
                value={output} onChange={(e) => setOutput(e.target.value)}
                placeholder={mode === 'outline' ? t('writing.generate_outline') : t('writing.generate_content')}
                disabled={isGenerating} />
              {output && mode === 'content' && (
                <div style={{ display: 'flex', gap: 6, alignItems: 'flex-start' }}>
                  <input className="form-input" style={{ flex: 1, fontSize: 12 }} value={rewriteInstruction}
                    onChange={(e) => setRewriteInstruction(e.target.value)}
                    placeholder={t('writing.extra_instructions_placeholder')} disabled={isRewriting} />
                  <button className="btn btn-sm" style={{ background: 'linear-gradient(135deg, #4A90D9, #7B68EE)', color: '#fff', border: 'none', whiteSpace: 'nowrap' }}
                    onClick={() => handleRewrite()} disabled={isRewriting || !output.trim()}>
                    {isRewriting ? t('writing.generating') : '🤖 AI ' + t('canvas.edit')}
                  </button>
                </div>
              )}
            </>
          )}

          {/* ─── 审计结果 ─────────────────────── */}
          {mode === 'audit' && auditResult && (
            <div style={{ marginTop: 12 }}>
              <div style={{ padding: '6px 10px', borderRadius: 6, marginBottom: 8, fontSize: 13, fontWeight: 600,
                background: auditResult.passed ? 'rgba(80,200,120,0.15)' : 'rgba(231,76,60,0.15)',
                color: auditResult.passed ? '#50C878' : '#E74C3C' }}>
                {auditResult.passed ? '✅ ' + t('writing.audit_passed') : `❌ ${t('writing.audit_failed', { count: auditResult.critical_count })}`}
                {auditResult.issues.length > 0 && t('writing.audit_total_issues', { count: auditResult.total_issues })}
              </div>
              {auditResult.issues.map((issue, i) => (
                <div key={i} style={{ padding: '8px 10px', marginBottom: 6, borderRadius: 6,
                  background: 'var(--bg-card)', border: '1px solid var(--border-color)',
                  borderLeft: `3px solid ${issue.severity === 'critical' ? '#E74C3C' : issue.severity === 'warning' ? '#F39C12' : '#4A90D9'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 2 }}>
                    <div style={{ flex: 1 }}>
                      <span style={{ fontSize: 12, fontWeight: 600 }}>{issue.dimension}</span>
                      <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, marginLeft: 6,
                        background: issue.severity === 'critical' ? '#E74C3C' : issue.severity === 'warning' ? '#F39C12' : '#4A90D9', color: '#fff' }}>
                        {issue.severity}
                      </span>
                    </div>
                    <button className="btn btn-sm" style={{ fontSize: 10, padding: '2px 8px', color: '#50C878', flexShrink: 0 }}
                      onClick={async () => {
                        setMode('content');
                        setRewriteInstruction(issue.suggestion || `${t('canvas.edit')}: ${issue.description}`);
                        showToast(t('writing.suggest_detail'));
                      }}>
                      🤖 AI {t('canvas.edit')}
                    </button>
                  </div>
                  <div style={{ fontSize: 12, color: '#ccc', marginBottom: 2 }}>{issue.description}</div>
                  {issue.location && <div style={{ fontSize: 11, color: '#888', fontStyle: 'italic' }}>「{issue.location}」</div>}
                  {issue.suggestion && <div style={{ fontSize: 11, color: '#50C878', marginTop: 2 }}>→ {issue.suggestion}</div>}
                </div>
              ))}
              {auditResult.overall_note && (
                <div style={{ fontSize: 12, color: '#a0a0b0', marginTop: 6, padding: 8, borderTop: '1px solid var(--border-color)' }}>
                  {auditResult.overall_note}
                </div>
              )}

              {auditResult.foreshadows_extracted && auditResult.foreshadows_extracted.length > 0 && (
                <div style={{ marginTop: 10, padding: '8px 10px', borderRadius: 6, background: 'rgba(243,156,18,0.08)', border: '1px solid rgba(243,156,18,0.3)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F39C12' }}>◈ {t('writing.foreshadows_extracted')}</span>
                    <button className="btn btn-sm" style={{ fontSize: 10, padding: '2px 8px', background: '#F39C12', color: '#fff', border: 'none' }}
                      onClick={handleCreateAllForeshadows}>
                      + {t('writing.create_all_foreshadows')}
                    </button>
                  </div>
                  <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>
                    {t('writing.foreshadows_extracted_hint', { count: auditResult.foreshadows_extracted.length })}
                  </div>
                  {auditResult.foreshadows_extracted.map((fs, i) => (
                    <div key={i} style={{ padding: '6px 8px', marginBottom: 4, borderRadius: 4, background: 'var(--bg-card)', borderLeft: `3px solid ${fs.type === 'hook' ? '#E8873A' : '#F39C12'}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: 12, fontWeight: 600 }}>
                          {fs.type === 'hook' ? '🔗' : '◈'} {fs.title}
                        </span>
                        <button className="btn btn-sm" style={{ fontSize: 10, padding: '1px 6px', color: '#F39C12' }}
                          onClick={() => handleCreateForeshadowBlock(fs)}>
                          + {t('writing.create_block')}
                        </button>
                      </div>
                      {fs.description && <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>{fs.description}</div>}
                      <div style={{ display: 'flex', gap: 6, marginTop: 3 }}>
                        {fs.urgency && (
                          <span style={{ fontSize: 10, padding: '1px 5px', borderRadius: 3, background: fs.urgency === 'high' ? '#E74C3C' : fs.urgency === 'medium' ? '#F39C12' : 'var(--bg-secondary)', color: '#fff' }}>
                            {fs.urgency}
                          </span>
                        )}
                        {fs.suggested_payoff_chapter && (
                          <span style={{ fontSize: 10, padding: '1px 5px', borderRadius: 3, background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
                            → {t('writing.payoff_chapter')}: {fs.suggested_payoff_chapter}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WritingPanel;
