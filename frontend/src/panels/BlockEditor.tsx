import React, { useState, useEffect } from 'react';
import { useCanvasStore } from '../store/canvasStore';
import { useProjectStore } from '../store/projectStore';
import { useUIStore } from '../store/uiStore';
import { BlockData, BlockType, BLOCK_COLORS, BLOCK_LABELS } from '../types/blocks';
import { useT } from '../i18n/useT';

const FIELD_GROUPS: Record<string, { key: string; label: string; type: 'text' | 'textarea' | 'number' | 'select'; options?: string[] }[]> = {
  // ─── 角色类 ─────────────────────────────────────────
  CHARACTER: [
    { key: 'name', label: '名称', type: 'text' },
    { key: 'want', label: '外在目标 (Want)', type: 'textarea' },
    { key: 'need', label: '内在渴望 (Need)', type: 'textarea' },
    { key: 'fatal_flaw', label: '致命缺陷', type: 'textarea' },
    { key: 'surface_personality', label: '表面性格', type: 'textarea' },
    { key: 'role_archetype', label: '角色定位', type: 'text' },
    { key: 'superpower', label: '能力/特长', type: 'textarea' },
    { key: 'voice_style', label: '说话风格', type: 'textarea' },
    { key: 'appearance', label: '外貌', type: 'textarea' },
    { key: 'age', label: '年龄', type: 'text' },
  ],
  PERSONALITY: [
    { key: 'character_id', label: '角色ID', type: 'text' },
    { key: 'core_values', label: '核心价值观', type: 'textarea' },
    { key: 'behavior_patterns', label: '行为模式', type: 'textarea' },
    { key: 'dramatica_function', label: 'Dramatica功能', type: 'select', options: ['主角', '影响角色', '情感判断', '理性思考'] },
  ],
  GROWTH: [
    { key: 'character_id', label: '角色ID', type: 'text' },
    { key: 'arc_type', label: '弧线类型', type: 'select', options: ['正向成长', '堕落', '救赎', '幻灭', '蜕变'] },
    { key: 'start_state', label: '起点状态', type: 'textarea' },
    { key: 'end_state', label: '终点状态', type: 'textarea' },
    { key: 'keystone_moments', label: '关键时刻', type: 'textarea' },
  ],
  BACKSTORY: [
    { key: 'character_id', label: '角色ID', type: 'text' },
    { key: 'origin', label: '起源', type: 'textarea' },
    { key: 'formative_events', label: '成型事件', type: 'textarea' },
    { key: 'secrets', label: '秘密', type: 'textarea' },
  ],
  CURRENT_STATE: [
    { key: 'character_id', label: '角色ID', type: 'text' },
    { key: 'chapter', label: '章节', type: 'number' },
    { key: 'physical_condition', label: '生理状态', type: 'textarea' },
    { key: 'psychological_condition', label: '心理状态', type: 'textarea' },
    { key: 'active_goals', label: '当前目标', type: 'textarea' },
    { key: 'emotional_state', label: '情绪状态', type: 'textarea' },
  ],
  INFORMATION_BOUNDARY: [
    { key: 'character_id', label: '角色ID', type: 'text' },
    { key: 'chapter', label: '章节', type: 'number' },
    { key: 'confirmed_knowledge', label: '已知信息', type: 'textarea' },
    { key: 'wrongly_believes', label: '错误信念', type: 'textarea' },
    { key: 'dramatic_irony', label: '戏剧反讽', type: 'textarea' },
  ],
  OMNISCIENT_LAYER: [
    { key: 'true_facts', label: '真实事实', type: 'textarea' },
    { key: 'reader_reveal_plan', label: '读者揭示计划', type: 'textarea' },
  ],
  // ─── 世界类 ─────────────────────────────────────────
  WORLDVIEW: [
    { key: 'world_name', label: '世界名称', type: 'text' },
    { key: 'fundamental_rules', label: '核心规则', type: 'textarea' },
    { key: 'cosmology', label: '宇宙结构', type: 'textarea' },
    { key: 'power_system', label: '力量体系', type: 'textarea' },
    { key: 'tone', label: '整体基调', type: 'text' },
  ],
  FACTION: [
    { key: 'name', label: '名称', type: 'text' },
    { key: 'ideology', label: '意识形态', type: 'textarea' },
    { key: 'goal', label: '目标', type: 'textarea' },
    { key: 'resources', label: '资源', type: 'textarea' },
    { key: 'weakness', label: '弱点', type: 'textarea' },
  ],
  RULE_CONSTRAINT: [
    { key: 'rule_name', label: '规则名称', type: 'text' },
    { key: 'rule_type', label: '规则类型', type: 'select', options: ['物理法则', '社会规则', '魔法规则', '禁忌', '技术限制'] },
    { key: 'mechanism', label: '运作机制', type: 'textarea' },
    { key: 'consequence_of_breaking', label: '违反后果', type: 'textarea' },
  ],
  WORLD_DEVELOPMENT: [
    { key: 'aspect', label: '发展方面', type: 'text' },
    { key: 'current_state', label: '当前状态', type: 'textarea' },
    { key: 'trajectory', label: '发展轨迹', type: 'textarea' },
    { key: 'key_events', label: '关键事件', type: 'textarea' },
  ],
  TIMESTAMP: [
    { key: 'era_name', label: '时代名称', type: 'text' },
    { key: 'time_range', label: '时间范围', type: 'text' },
    { key: 'key_changes', label: '关键变化', type: 'textarea' },
  ],
  // ─── 叙事结构类 ─────────────────────────────────────
  TIMELINE: [
    { key: 'timeline_name', label: '时间线名称', type: 'text' },
    { key: 'timeline_type', label: '类型', type: 'select', options: ['主线', '支线', '回忆线', '平行线'] },
    { key: 'pov_characters', label: '视角角色', type: 'textarea' },
  ],
  SCENE: [
    { key: 'title', label: '标题', type: 'text' },
    { key: 'scene_goal', label: '场景目标', type: 'textarea' },
    { key: 'emotion_target', label: '情绪目标', type: 'textarea' },
    { key: 'tension_level', label: '张力级别 (1-10)', type: 'number' },
    { key: 'scene_type', label: '场景类型', type: 'text' },
    { key: 'what_happens', label: '场景内容', type: 'textarea' },
    { key: 'characters_present', label: '在场角色', type: 'textarea' },
  ],
  EVENT: [
    { key: 'title', label: '标题', type: 'text' },
    { key: 'what_happens', label: '发生了什么', type: 'textarea' },
    { key: 'event_type', label: '事件类型', type: 'text' },
    { key: 'immediate_effects', label: '即时影响', type: 'textarea' },
  ],
  GOAL: [
    { key: 'surface_goal', label: '表面目标', type: 'textarea' },
    { key: 'deep_goal', label: '深层目标', type: 'textarea' },
    { key: 'obstacle', label: '障碍', type: 'textarea' },
    { key: 'stakes', label: '代价', type: 'textarea' },
  ],
  CONFLICT: [
    { key: 'title', label: '标题', type: 'text' },
    { key: 'conflict_type', label: '冲突类型', type: 'select', options: ['人vs人', '人vs自然', '人vs社会', '人vs自我', '人vs命运', '人vs科技'] },
    { key: 'root_cause', label: '根源', type: 'textarea' },
    { key: 'surface_manifestation', label: '表面表现', type: 'textarea' },
    { key: 'resolution_type', label: '解决方式', type: 'select', options: ['妥协', '胜利', '失败', '共存', '升华'] },
  ],
  TURNING_POINT: [
    { key: 'title', label: '标题', type: 'text' },
    { key: 'turning_type', label: '转折类型', type: 'select', options: ['危机', '发现', '背叛', '牺牲', '觉醒', '重逢'] },
    { key: 'before_state', label: '转折前状态', type: 'textarea' },
    { key: 'trigger', label: '触发事件', type: 'textarea' },
    { key: 'after_state', label: '转折后状态', type: 'textarea' },
  ],
  HOOK: [
    { key: 'title', label: '标题', type: 'text' },
    { key: 'hook_type', label: '悬念类型', type: 'select', options: ['身份悬念', '命运悬念', '真相悬念', '道德困境', '时间炸弹'] },
    { key: 'content_planted', label: '埋下了什么', type: 'textarea' },
    { key: 'plant_chapter', label: '埋设章节', type: 'text' },
    { key: 'payoff_chapter', label: '回收章节', type: 'text' },
    { key: 'content_resolved', label: '如何回收', type: 'textarea' },
  ],
  FORESHADOW: [
    { key: 'title', label: '标题', type: 'text' },
    { key: 'hint_content', label: '暗示内容', type: 'textarea' },
    { key: 'plant_chapter', label: '埋设章节', type: 'text' },
    { key: 'payoff_chapter', label: '回收章节', type: 'text' },
    { key: 'payoff_content', label: '回收方式', type: 'textarea' },
  ],
  SURPRISE: [
    { key: 'title', label: '标题', type: 'text' },
    { key: 'surprise_type', label: '意外类型', type: 'select', options: ['身份揭露', '真相反转', '命运逆转', '关系揭露', '世界观颠覆'] },
    { key: 'revelation', label: '揭示内容', type: 'textarea' },
    { key: 'setup_required', label: '所需铺垫', type: 'textarea' },
  ],
  // ─── 关系类 ─────────────────────────────────────────
  RELATIONSHIP: [
    { key: 'party_a_id', label: '角色A ID', type: 'text' },
    { key: 'party_b_id', label: '角色B ID', type: 'text' },
    { key: 'relationship_type', label: '关系类型', type: 'select', options: ['盟友', '对手', '恋人', '师徒', '亲人', '上下级', '暗敌'] },
    { key: 'dynamic', label: '关系动态', type: 'textarea' },
    { key: 'history', label: '关系历史', type: 'textarea' },
    { key: 'intensity', label: '强度 (1-10)', type: 'number' },
  ],
  FACTION_RELATION: [
    { key: 'faction_a_id', label: '势力A ID', type: 'text' },
    { key: 'faction_b_id', label: '势力B ID', type: 'text' },
    { key: 'relation_type', label: '关系类型', type: 'select', options: ['同盟', '敌对', '冷战', '贸易', '从属', '暗中合作'] },
    { key: 'key_events', label: '关键事件', type: 'textarea' },
    { key: 'current_tension', label: '当前紧张度 (1-10)', type: 'number' },
  ],
  // ─── 表达类 ─────────────────────────────────────────
  ATMOSPHERE: [
    { key: 'name', label: '意境名称', type: 'text' },
    { key: 'sensory_details', label: '感官细节', type: 'textarea' },
    { key: 'emotional_tone', label: '情感基调', type: 'text' },
    { key: 'associated_elements', label: '关联元素', type: 'textarea' },
  ],
  EMOTION_TARGET: [
    { key: 'chapter', label: '章节', type: 'number' },
    { key: 'primary_emotion', label: '主要情绪', type: 'select', options: ['紧张', '悲伤', '喜悦', '恐惧', '愤怒', '温馨', '震撼', '困惑'] },
    { key: 'intensity', label: '强度 (1-10)', type: 'number' },
    { key: 'trigger', label: '触发原因', type: 'textarea' },
    { key: 'resolution', label: '情绪释放', type: 'textarea' },
  ],
  RHYTHM: [
    { key: 'chapter', label: '章节', type: 'number' },
    { key: 'rhythm_type', label: '节奏类型', type: 'select', options: ['加速', '减速', '急转', '平稳', '高潮', '沉淀'] },
    { key: 'pacing_notes', label: '节拍说明', type: 'textarea' },
    { key: 'transition_style', label: '过渡风格', type: 'text' },
  ],
  THEME_STATEMENT: [
    { key: 'theme', label: '主题', type: 'textarea' },
    { key: 'exploration_approach', label: '探索方式', type: 'textarea' },
    { key: 'counter_argument', label: '反方论点', type: 'textarea' },
  ],
  LENS: [
    { key: 'lens_type', label: '镜头类型', type: 'select', options: ['特写', '远景', '鸟瞰', '跟随', '蒙太奇', '主观视角'] },
    { key: 'focus_description', label: '焦点描述', type: 'textarea' },
    { key: 'application_notes', label: '应用说明', type: 'textarea' },
  ],
  // ─── 剧本专属类 ─────────────────────────────────────
  SCENE_HEADING: [
    { key: 'interior_exterior', label: '内/外', type: 'select', options: ['内景', '外景', '内外'] },
    { key: 'location', label: '地点', type: 'text' },
    { key: 'time_of_day', label: '时间', type: 'select', options: ['日', '夜', '晨', '昏', '延续'] },
  ],
  ACTION_LINE: [
    { key: 'character_id', label: '角色ID', type: 'text' },
    { key: 'description', label: '动作描述', type: 'textarea' },
    { key: 'continuation_note', label: '连续说明', type: 'textarea' },
  ],
  DIALOGUE: [
    { key: 'character_id', label: '角色ID', type: 'text' },
    { key: 'parenthetical', label: '提示词', type: 'text' },
    { key: 'line_text', label: '台词', type: 'textarea' },
    { key: 'delivery_note', label: '演绎说明', type: 'textarea' },
  ],
  VISUAL_MOTIF: [
    { key: 'motif_name', label: '主题名称', type: 'text' },
    { key: 'visual_description', label: '视觉描述', type: 'textarea' },
    { key: 'symbolic_meaning', label: '象征意义', type: 'textarea' },
  ],
  // ─── 大纲类 ─────────────────────────────────────────
  // 参考 Dramatica-Flow 叙事架构：StoryOutline → Sequence → ChapterOutline → Beat → Scene

  STORY_SYNOPSIS: [
    { key: 'title', label: '故事标题', type: 'text' },
    { key: 'logline', label: '一句话梗概', type: 'textarea' },
    { key: 'synopsis', label: '完整故事简介', type: 'textarea' },
    { key: 'genre', label: '类型标签', type: 'text' },
    { key: 'theme', label: '核心主题', type: 'textarea' },
    { key: 'tone', label: '基调风格', type: 'textarea' },
    { key: 'protagonists', label: '主要角色', type: 'textarea' },
    { key: 'antagonists', label: '冲突/对手', type: 'textarea' },
    { key: 'setting', label: '背景设定', type: 'textarea' },
  ],

  STORY_OUTLINE: [
    { key: 'title', label: '故事标题', type: 'text' },
    { key: 'logline', label: '一句话梗概', type: 'textarea' },
    { key: 'genre', label: '类型', type: 'text' },
    { key: 'divider_acts', label: '—— 三幕结构 ——', type: 'text' },
    { key: 'act1_summary', label: '第一幕·建置', type: 'textarea' },
    { key: 'act2_summary', label: '第二幕·对抗', type: 'textarea' },
    { key: 'act3_summary', label: '第三幕·结局', type: 'textarea' },
    { key: 'divider_structure', label: '—— 剧情结构 ——', type: 'text' },
    { key: 'key_turning_points', label: '关键转折点', type: 'textarea' },
    { key: 'central_conflict', label: '核心冲突', type: 'textarea' },
    { key: 'climax_design', label: '高潮设计', type: 'textarea' },
    { key: 'ending_type', label: '结局类型', type: 'select', options: ['圆满结局', '悲剧结局', '开放结局', '反转结局', '留白结局'] },
    { key: 'emotional_roadmap', label: '情感路线', type: 'textarea' },
  ],

  CHAPTER_OUTLINE: [
    { key: 'chapter_number', label: '章节号', type: 'number' },
    { key: 'title', label: '章节标题', type: 'text' },
    { key: 'summary', label: '章节概要', type: 'textarea' },
    { key: 'narrative_goal', label: '叙事目标', type: 'textarea' },
    { key: 'dramatic_function', label: '戏剧功能', type: 'select', options: ['建置', '激励', '转折', '中点', '危机', '高潮', '揭示', '抉择', '后果', '过渡'] },
    { key: 'divider_beats', label: '—— 节拍规划 ——', type: 'text' },
    { key: 'beat1_desc', label: '节拍1 描述', type: 'textarea' },
    { key: 'beat2_desc', label: '节拍2 描述', type: 'textarea' },
    { key: 'beat3_desc', label: '节拍3 描述', type: 'textarea' },
    { key: 'pov_character', label: '视角角色', type: 'text' },
    { key: 'target_words', label: '目标字数', type: 'number' },
    { key: 'emotional_arc', label: '情感弧线', type: 'textarea' },
    { key: 'status', label: '状态', type: 'select', options: ['planned', 'outlined', 'generated', 'approved'] },
  ],

  CHAPTER_DETAIL: [
    { key: 'chapter_number', label: '章节号', type: 'number' },
    { key: 'title', label: '章节标题', type: 'text' },
    { key: 'divider_scenes', label: '—— 场景规划 ——', type: 'text' },
    { key: 'scene1_heading', label: '场景1 标题', type: 'text' },
    { key: 'scene1_content', label: '场景1 内容', type: 'textarea' },
    { key: 'scene2_heading', label: '场景2 标题', type: 'text' },
    { key: 'scene2_content', label: '场景2 内容', type: 'textarea' },
    { key: 'scene3_heading', label: '场景3 标题', type: 'text' },
    { key: 'scene3_content', label: '场景3 内容', type: 'textarea' },
    { key: 'divider_other', label: '—— 其他 ——', type: 'text' },
    { key: 'key_conflicts', label: '核心冲突', type: 'textarea' },
    { key: 'character_goals', label: '角色目标', type: 'textarea' },
    { key: 'writing_notes', label: '写作备注', type: 'textarea' },
  ],
  // ─── 特殊类 ─────────────────────────────────────────
  STORY_CARD: [
    { key: 'card_id', label: '故事卡编号', type: 'text' },
    { key: 'card_name', label: '卡名称', type: 'text' },
    { key: 'genre', label: '类型标签', type: 'text' },
    { key: 'writing_modifier', label: '写作风格要求', type: 'textarea' },
    { key: 'reference_works', label: '参考作品', type: 'textarea' },
  ],
  READER_EMOTION_CURVE: [
    { key: 'chapters', label: '覆盖章节', type: 'text' },
    { key: 'peak_points', label: '高峰点', type: 'textarea' },
    { key: 'valley_points', label: '低谷点', type: 'textarea' },
    { key: 'overall_trajectory', label: '整体走向', type: 'select', options: ['递增', '递减', '波浪', '先抑后扬', '先扬后抑', '平稳'] },
  ],
};

const BlockEditor: React.FC = () => {
  const { t } = useT();
  const { selectedBlock } = useCanvasStore();
  const { currentProject, updateBlock } = useProjectStore();
  const [localContent, setLocalContent] = useState<Record<string, any>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiHint, setAiHint] = useState('');

  useEffect(() => {
    if (selectedBlock) {
      setLocalContent({ ...(selectedBlock.content || {}) });
    }
  }, [selectedBlock?.id]);

  if (!selectedBlock || !currentProject) {
    return (
      <div className="panel">
        <div className="panel-header">{t('editor.title')}</div>
        <div className="panel-body">
          <div style={{ color: '#6c6c80', fontSize: 13, textAlign: 'center', padding: 40 }}>
            {t('editor.no_selection')}
          </div>
        </div>
      </div>
    );
  }

  const fields = FIELD_GROUPS[selectedBlock.type] || [];
  const color = BLOCK_COLORS[selectedBlock.type] || '#999';

  const handleFieldChange = (key: string, value: any) => {
    const updated = { ...localContent, [key]: value };
    setLocalContent(updated);
  };

  const handleSave = async () => {
    setIsSaving(true);
    await updateBlock(currentProject.id, selectedBlock.id, { content: localContent });
    setIsSaving(false);
  };

  const handleBlur = () => {
    handleSave();
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <span>
          <span style={{ color, fontWeight: 700 }}>■ </span>
          {BLOCK_LABELS[selectedBlock.type] || selectedBlock.type}
          <span style={{ fontSize: 11, color: '#6c6c80', marginLeft: 6 }}>({selectedBlock.type})</span>
        </span>
        <button className="btn btn-sm btn-ghost" onClick={() => useCanvasStore.getState().setSelectedBlock(null)}>
          ✕
        </button>
      </div>
      <div className="panel-body">
        <div className="block-editor">
          <div style={{ fontSize: 12, color: '#a0a0b0', marginBottom: 8 }}>
            完整度: {Math.round((selectedBlock.completeness || 0) * 100)}%
          </div>

          {fields.map((field) => (
            field.key.startsWith('divider_') ? (
              <div key={field.key} style={{
                borderTop: '1px solid var(--border-color)',
                margin: '12px 0 6px 0',
                paddingTop: 8,
                fontSize: 11,
                fontWeight: 700,
                color: 'var(--text-secondary)',
                letterSpacing: 1,
              }}>
                {field.label}
              </div>
            ) : (
            <div className="field-group" key={field.key}>
              <div className="field-label">{field.label}</div>
              {field.type === 'number' ? (
                <input
                  className="form-input"
                  type="number"
                  value={localContent[field.key] ?? ''}
                  onChange={(e) => handleFieldChange(field.key, parseInt(e.target.value) || 0)}
                  onBlur={handleBlur}
                />
              ) : field.type === 'select' ? (
                <select
                  className="form-input"
                  value={localContent[field.key] ?? ''}
                  onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  onBlur={handleBlur}
                >
                  <option value="">-- 选择 --</option>
                  {(field.options || []).map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              ) : field.type === 'textarea' ? (
                <textarea
                  className="form-textarea"
                  rows={3}
                  value={localContent[field.key] ?? ''}
                  onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  onBlur={handleBlur}
                  placeholder={`输入${field.label}...`}
                />
              ) : (
                <input
                  className="form-input"
                  type="text"
                  value={localContent[field.key] ?? ''}
                  onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  onBlur={handleBlur}
                  placeholder={`输入${field.label}...`}
                />
              )}
            </div>
            )
          ))}

          {fields.length === 0 && (
            <div style={{ color: '#6c6c80', fontSize: 13, padding: 20, textAlign: 'center' }}>
              该块类型暂无预设字段
            </div>
          )}

          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={isSaving}
            style={{ width: '100%', marginTop: 8 }}
          >
            {isSaving ? '保存中...' : '保存'}
          </button>

          {/* AI生成提示词 */}
          <div style={{ marginTop: 12, borderTop: '1px solid var(--border-color)', paddingTop: 10 }}>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>🤖 AI 生成条件（可选）</div>
            <textarea
              className="form-textarea"
              rows={2}
              value={aiHint}
              onChange={(e) => setAiHint(e.target.value)}
              placeholder={`例如：主角是性格内向的少年，故事发生在一个蒸汽朋克世界...`}
              style={{ fontSize: 12 }}
            />
            <button
              className="btn"
              style={{
                width: '100%', marginTop: 6,
                background: 'linear-gradient(135deg, #4A90D9, #7B68EE)',
                color: '#fff',
                border: 'none',
              }}
              onClick={async () => {
                setAiGenerating(true);
                try {
                  const res = await fetch(`/api/projects/${currentProject.id}/generate/block-content`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ block_id: selectedBlock.id, field: 'all', hint: aiHint }),
                  });
                  if (res.ok) {
                    const data = await res.json();
                    setLocalContent(data.merged_content || {});
                    await updateBlock(currentProject.id, selectedBlock.id, { content: data.merged_content });
                  }
                } catch {}
                setAiGenerating(false);
              }}
              disabled={aiGenerating}
            >
              {aiGenerating ? '🤖 生成中...' : '🤖 按条件生成'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BlockEditor;
