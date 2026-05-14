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

interface AuditResult {
  passed: boolean;
  issues: AuditIssue[];
  critical_count: number;
  total_issues: number;
  overall_note?: string;
}

const PROSE_STYLES = ['标准文笔', '华丽辞藻', '朴实白描', '幽默诙谐', '冷峻犀利', '诗意浪漫', '简洁明快'];
const POV_OPTIONS = ['', '多视角轮换', '限制第三人称', '全知叙事', '第一人称', '无焦点群像'];
const DENSITY_OPTIONS = ['', '厚重史诗', '极简风格', '标准叙事', '意识流', '诗化散文'];
const TONE_OPTIONS = ['冷峻克制', '道德灰度', '热血燃向'];

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

  const selectedBlock = outlineBlocks.find((b) => b.id === selectedBlockId);

  const handleGenerateOutline = async () => {
    if (!currentProject) return;
    setIsGenerating(true);
    setOutput('');
    setStage('正在生成细纲...');
    await generateOutline(
      currentProject.id, chapterNum, additionalInstructions,
      (text) => setOutput((prev) => prev + text),
      () => { setStage(null); setIsGenerating(false); showToast('细纲生成完成'); loadProject(currentProject.id); },
      (err) => { setStage(null); setIsGenerating(false); showToast(err, 'error'); }
    );
  };

  const handleGenerateContent = async () => {
    if (!currentProject) return;
    setIsGenerating(true);
    setOutput('');
    setStage('正在收集相关块...');
    let fullContent = '';
    const detailBlock = selectedBlock?.type === 'CHAPTER_DETAIL' ? selectedBlock.id : undefined;
    await generateChapterContent(
      currentProject.id, chapterNum, true,
      (s, msg) => setStage(msg),
      (text) => { fullContent += text; setOutput(fullContent); },
      (result) => {
        setStage(null); setIsGenerating(false);
        showToast(`第${chapterNum}章生成完成，共${result.word_count}字`);
        loadProject(currentProject.id);
      },
      (err) => { setStage(null); setIsGenerating(false); showToast(err, 'error'); },
      (violations) => showToast(`发现${violations.length}处信息边界警告`, 'warning'),
      detailBlock
    );
  };

  const handleAudit = async () => {
    if (!currentProject) return;
    setIsAuditing(true);
    setAuditResult(null);
    showToast('正在审计...');
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
        });
        showToast(audit.passed ? '✅ 审计通过' : `发现${audit.critical_count}个严重问题`, audit.passed ? 'info' : 'warning');
      }
    } catch {
      showToast('审计请求失败', 'error');
    }
    setIsAuditing(false);
  };

  /** AI改写正文（支持选中部分 + 上下文定点修改） */
  const handleRewrite = async (issue?: AuditIssue) => {
    if (!currentProject || !output.trim()) return;
    setIsRewriting(true);
    showToast('正在AI修改...');
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

      const body: any = { chapter_num: chapterNum, instruction: rewriteInstruction || '请优化这段正文' };
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
        showToast(selectedText ? '✅ 选中部分已修改' : '✅ AI修改完成');
      } else {
        showToast('修改失败', 'error');
      }
    } catch {
      showToast('修改出错', 'error');
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
        showToast('✅ 正文已保存');
        loadProject(currentProject.id);
      } else {
        showToast('保存失败', 'error');
      }
    } catch {
      showToast('保存出错', 'error');
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
        showToast('写作风格已保存');
      } else {
        showToast('保存失败', 'error');
      }
    } catch {
      showToast('保存出错', 'error');
    }
  };

  const toggleTone = (t: string) => {
    setTone((prev) => prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]);
  };

  return (
    <div className="panel" style={{ width: '50%', minWidth: 420 }}>
      <div className="panel-header">
        <span>写作面板</span>
        <div style={{ display: 'flex', gap: 4 }}>
          <button className={`btn btn-sm ${mode === 'outline' ? 'btn-primary' : ''}`} onClick={() => setMode('outline')}>细纲</button>
          <button className={`btn btn-sm ${mode === 'content' ? 'btn-primary' : ''}`} onClick={() => setMode('content')}>正文</button>
          <button className={`btn btn-sm ${mode === 'audit' ? 'btn-primary' : ''}`} onClick={() => setMode('audit')}>审计</button>
        </div>
      </div>
      <div className="panel-body">
        <div className="writing-panel">

          {/* ─── 章节块选择器 ─────────────────── */}
          <div style={{ marginBottom: 12 }}>
            <label className="form-label">选择章节块</label>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
              {outlineBlocks.length === 0 ? (
                <span style={{ fontSize: 12, color: '#6c6c80' }}>
                  还没有章节块，先在画布上添加「章节细纲」或「章节大纲」块
                </span>
              ) : (
                outlineBlocks.map((ob) => (
                  <button key={ob.id} className={`btn btn-sm ${selectedBlockId === ob.id ? 'btn-primary' : ''}`}
                    style={{ fontSize: 11, borderLeft: `3px solid ${ob.type === 'CHAPTER_DETAIL' ? '#50C878' : '#4A90D9'}` }}
                    onClick={() => { setSelectedBlockId(ob.id); setChapterNum(ob.chapter_number); }}
                    title={ob.type === 'CHAPTER_DETAIL' ? '章节细纲（含场景）' : '章节大纲'}>
                    {ob.type === 'CHAPTER_DETAIL' ? '📄' : '📋'} 第{ob.chapter_number}章 {ob.title?.substring(0, 8) || ''}
                  </button>
                ))
              )}
            </div>
            {selectedBlock && (
              <div style={{ fontSize: 11, color: '#a0a0b0', marginTop: 4, padding: '4px 8px', background: 'var(--bg-card)', borderRadius: 4,
                borderLeft: `3px solid ${selectedBlock.type === 'CHAPTER_DETAIL' ? '#50C878' : '#4A90D9'}` }}>
                <span style={{ color: selectedBlock.type === 'CHAPTER_DETAIL' ? '#50C878' : '#4A90D9', fontWeight: 600 }}>
                  {selectedBlock.type === 'CHAPTER_DETAIL' ? '章节细纲' : '章节大纲'}
                </span>: {selectedBlock.summary?.substring(0, 120) || '无摘要'}
                {selectedBlock.type === 'CHAPTER_OUTLINE' && mode === 'content' && (
                  <span style={{ color: '#F39C12' }}> （建议选「章节细纲」块来生成正文）</span>
                )}
              </div>
            )}
          </div>

          {/* ─── 章节号 ─────────────────────────── */}
          <div className="chapter-selector" style={{ marginBottom: 8 }}>
            <label className="form-label" style={{ margin: 0 }}>章节号:</label>
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
              <label className="form-label">额外指令</label>
              <textarea className="form-textarea" rows={2} value={additionalInstructions}
                onChange={(e) => setAdditionalInstructions(e.target.value)}
                placeholder="给AI额外的写作指令..." disabled={isGenerating} />
            </div>
          )}

          {/* ─── 写作风格 ───────────────────────── */}
          <div style={{ marginBottom: 12, border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden' }}>
            <div style={{ padding: '8px 12px', cursor: 'pointer', fontSize: 12, fontWeight: 600,
              background: 'var(--bg-card)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
              onClick={() => setIsStyleExpanded(!isStyleExpanded)}>
              <span>🎨 写作风格</span>
              <span style={{ fontSize: 10, color: '#888' }}>{isStyleExpanded ? '收起 ▲' : '展开 ▼'}</span>
            </div>
            {isStyleExpanded && (
              <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div>
                  <label className="form-label">文笔风格</label>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 2 }}>
                    {PROSE_STYLES.map((s) => (
                      <button key={s} className={`btn btn-sm ${proseStyle === s ? 'btn-primary' : ''}`}
                        onClick={() => setProseStyle(proseStyle === s ? '' : s)} style={{ fontSize: 11 }}>{s}</button>
                    ))}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <div style={{ flex: 1 }}>
                    <label className="form-label">叙事视角</label>
                    <select className="form-input" value={narrativePov}
                      onChange={(e) => setNarrativePov(e.target.value)} style={{ fontSize: 11, marginTop: 2 }}>
                      {POV_OPTIONS.map((o) => <option key={o} value={o}>{o || '(默认)'}</option>)}
                    </select>
                  </div>
                  <div style={{ flex: 1 }}>
                    <label className="form-label">语言密度</label>
                    <select className="form-input" value={languageDensity}
                      onChange={(e) => setLanguageDensity(e.target.value)} style={{ fontSize: 11, marginTop: 2 }}>
                      {DENSITY_OPTIONS.map((o) => <option key={o} value={o}>{o || '(默认)'}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="form-label">基调标签</label>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 2 }}>
                    {TONE_OPTIONS.map((t) => (
                      <button key={t} className={`btn btn-sm ${tone.includes(t) ? 'btn-primary' : ''}`}
                        onClick={() => toggleTone(t)} style={{ fontSize: 11 }}>{t}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="form-label">自定义指令</label>
                  <textarea className="form-textarea" rows={2} value={customInstructions}
                    onChange={(e) => setCustomInstructions(e.target.value)}
                    placeholder="额外的写作风格要求..." style={{ fontSize: 11 }} />
                </div>
                <button className="btn btn-sm btn-primary" onClick={handleSaveStyle} style={{ alignSelf: 'flex-end' }}>保存风格</button>
              </div>
            )}
          </div>

          {/* ─── 操作按钮（非审计模式） ─────────── */}
          {mode !== 'audit' && (
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary"
                onClick={mode === 'outline' ? handleGenerateOutline : handleGenerateContent}
                disabled={isGenerating || !currentProject}>
                {isGenerating ? <><span className="loading-spinner" /> 生成中...</> : (mode === 'outline' ? '生成细纲' : '生成正文')}
              </button>
              <button className="btn" onClick={() => { setOutput(''); setStage(null); }} disabled={isGenerating}>清空</button>
              {output && mode === 'content' && (
                <button className="btn btn-sm" onClick={handleSaveContent} style={{ color: '#50C878' }}>💾 保存正文</button>
              )}
            </div>
          )}

          {/* ─── 操作按钮（审计模式） ─────────── */}
          {mode === 'audit' && (
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary" onClick={handleAudit} disabled={isAuditing || !currentProject}>
                {isAuditing ? '审计中...' : '🔍 运行审计'}
              </button>
              <button className="btn" onClick={() => { setOutput(''); setStage(null); setAuditResult(null); }} disabled={isGenerating}>清空</button>
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
                placeholder={mode === 'outline' ? '点击「生成细纲」开始创作' : '点击「生成正文」开始创作\n\n选中某段文字再点AI修改可以定点修改'}
                disabled={isGenerating} />
              {output && mode === 'content' && (
                <div style={{ display: 'flex', gap: 6, alignItems: 'flex-start' }}>
                  <input className="form-input" style={{ flex: 1, fontSize: 12 }} value={rewriteInstruction}
                    onChange={(e) => setRewriteInstruction(e.target.value)}
                    placeholder="输入修改要求，如：让对话更自然、增加环境描写..." disabled={isRewriting} />
                  <button className="btn btn-sm" style={{ background: 'linear-gradient(135deg, #4A90D9, #7B68EE)', color: '#fff', border: 'none', whiteSpace: 'nowrap' }}
                    onClick={() => handleRewrite()} disabled={isRewriting || !output.trim()}>
                    {isRewriting ? '修改中...' : '🤖 AI修改'}
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
                {auditResult.passed ? '✅ 审计通过' : `❌ 发现 ${auditResult.critical_count} 个严重问题`}
                {auditResult.issues.length > 0 && `（共 ${auditResult.total_issues} 条）`}
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
                        setRewriteInstruction(issue.suggestion || `修复: ${issue.description}`);
                        showToast('切换到正文模式，点击AI修改');
                      }}>
                      🤖 AI修复
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
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WritingPanel;
