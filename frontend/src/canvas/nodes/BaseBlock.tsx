import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { BlockData, BLOCK_COLORS, BLOCK_LABELS } from '../../types/blocks';

const BLOCK_ICONS: Record<string, string> = {
  CHARACTER: 'C', SCENE: 'S', TIMELINE: 'T', EVENT: 'E', HOOK: '?',
  WORLDVIEW: 'W', FACTION: 'F', OMNISCIENT_LAYER: 'O', GOAL: 'G',
  CONFLICT: '!', TURNING_POINT: '⚡', RELATIONSHIP: '❤', FORESHADOW: '◈',
  PERSONALITY: 'Ps', GROWTH: 'Gr', BACKSTORY: 'Bs', CURRENT_STATE: 'Cs',
  INFORMATION_BOUNDARY: 'Ib', RULE_CONSTRAINT: 'Rc', WORLD_DEVELOPMENT: 'Wd',
  TIMESTAMP: 'Ts', SURPRISE: '!!', FACTION_RELATION: 'Fr', ATMOSPHERE: 'At',
  EMOTION_TARGET: 'Et', RHYTHM: 'Rh', THEME_STATEMENT: 'Th', LENS: 'Le',
  SCENE_HEADING: 'Sh', ACTION_LINE: 'Al', DIALOGUE: 'D', VISUAL_MOTIF: 'Vm',
  READER_EMOTION_CURVE: 'Em',
  STORY_CARD: '★',
  STORY_OUTLINE: '☰',
  CHAPTER_OUTLINE: '☷',
  CHAPTER_DETAIL: '☰',
  STORY_SYNOPSIS: '📖',
};

function getBlockTitle(data: BlockData): string {
  const c = data.content || {};
  if (data.type === 'CHARACTER') return c.name || '新角色';
  if (data.type === 'SCENE') return c.title || '新场景';
  if (data.type === 'TIMELINE') return c.timeline_name || '新时间线';
  if (data.type === 'EVENT') return c.title || '新事件';
  if (data.type === 'HOOK') return c.title || '新悬念';
  if (data.type === 'WORLDVIEW') return c.world_name || '新世界观';
  if (data.type === 'FACTION') return c.name || '新势力';
  if (data.type === 'GOAL') return c.surface_goal || '新目标';
  if (data.type === 'CONFLICT') return c.title || '新冲突';
  if (data.type === 'TURNING_POINT') return c.title || '新转折';
  if (data.type === 'FORESHADOW') return c.title || '新铺垫';
  if (data.type === 'SURPRISE') return c.title || '新意外';
  if (data.type === 'RELATIONSHIP') return c.relationship_type || '新关系';
  if (data.type === 'FACTION_RELATION') return c.relation_type || '势力关系';
  if (data.type === 'ATMOSPHERE') return c.name || '新意境';
  if (data.type === 'RULE_CONSTRAINT') return c.rule_name || '新规则';
  if (data.type === 'WORLD_DEVELOPMENT') return c.aspect || '世界发展';
  if (data.type === 'VISUAL_MOTIF') return c.motif_name || '视觉主题';
  if (data.type === 'LENS') return c.lens_type || '镜头';
  if (data.type === 'SCENE_HEADING') return [c.interior_exterior, c.location, c.time_of_day].filter(Boolean).join(' ') || '场景头';
  if (data.type === 'ACTION_LINE') return (c.description || '').substring(0, 30) || '动作行';
  if (data.type === 'DIALOGUE') return (c.line_text || '').substring(0, 30) || '对白';
  if (data.type === 'STORY_CARD') return c.card_name || c.card_id || '故事卡';
  if (data.type === 'READER_EMOTION_CURVE') return `${c.overall_trajectory || '曲线'}`;
  if (data.type === 'THEME_STATEMENT') return (c.theme || '').substring(0, 30) || '主题';
  if (data.type === 'EMOTION_TARGET') return `第${c.chapter || '?'}章 ${c.primary_emotion || ''}`;
  if (data.type === 'RHYTHM') return `第${c.chapter || '?'}章 ${c.rhythm_type || ''}`;
  if (data.type === 'CURRENT_STATE') return c.character_id ? `角色${c.character_id} 第${c.chapter || '?'}章` : '当前状态';
  if (data.type === 'INFORMATION_BOUNDARY') return c.character_id ? `角色${c.character_id} 第${c.chapter || '?'}章` : '信息边界';
  if (data.type === 'TIMESTAMP') return c.era_name || '新时间戳';
  if (data.type === 'STORY_OUTLINE') return c.title || '故事大纲';
  if (data.type === 'CHAPTER_OUTLINE') return `第${c.chapter_number || '?'}章 ${c.title || '大纲'}`;
  if (data.type === 'CHAPTER_DETAIL') return `第${c.chapter_number || '?'}章细纲: ${c.title || ''}`;
  if (data.type === 'STORY_SYNOPSIS') return c.title || '故事简介';
  return BLOCK_LABELS[data.type] || data.type;
}

/**
 * 按块类型返回要在画布块上显示的关键字段信息（最多3行）
 */
function getBlockSummary(data: BlockData): { label: string; value: string }[] {
  const c = data.content || {};

  switch (data.type) {
    // ─── 角色类 ────────────────────────────────
    case 'PERSONALITY':
      return [
        { label: '功能', value: c.dramatica_function || '?' },
        { label: '价值观', value: trunc(c.core_values, 28) },
      ];
    case 'GROWTH':
      return [
        { label: '弧线', value: c.arc_type || '?' },
        { label: '终点', value: trunc(c.end_state, 28) },
      ];
    case 'BACKSTORY':
      return [
        { label: '起源', value: trunc(c.origin, 30) },
        { label: '秘密', value: trunc(c.secrets, 20) },
      ];
    case 'CURRENT_STATE':
      return [
        { label: '心理', value: trunc(c.psychological_condition, 30) },
        { label: '情绪', value: trunc(c.emotional_state, 20) },
      ];
    case 'INFORMATION_BOUNDARY':
      return [
        { label: '已知', value: trunc(c.confirmed_knowledge, 30) },
        { label: '误信', value: trunc(c.wrongly_believes, 20) },
      ];
    case 'OMNISCIENT_LAYER':
      return [
        { label: '事实', value: trunc(c.true_facts, 30) },
      ];
    // ─── 世界类 ────────────────────────────────
    case 'WORLDVIEW':
      return [
        { label: '规则', value: trunc(c.fundamental_rules, 30) },
      ];
    case 'FACTION':
      return [
        { label: '信条', value: trunc(c.ideology, 30) },
      ];
    case 'RULE_CONSTRAINT':
      return [
        { label: '类型', value: c.rule_type || '?' },
        { label: '机制', value: trunc(c.mechanism, 25) },
      ];
    case 'WORLD_DEVELOPMENT':
      return [
        { label: '现状', value: trunc(c.current_state, 30) },
      ];
    case 'TIMESTAMP':
      return [
        { label: '范围', value: c.time_range || '?' },
        { label: '变化', value: trunc(c.key_changes, 25) },
      ];
    // ─── 叙事结构类 ────────────────────────────
    case 'TIMELINE':
      return [
        { label: '类型', value: c.timeline_type || '?' },
        { label: '视角', value: trunc(c.pov_characters, 25) },
      ];
    case 'EVENT':
      return [
        { label: '内容', value: trunc(c.what_happens, 35) },
      ];
    case 'GOAL':
      return [
        { label: '深层目标', value: trunc(c.deep_goal, 30) },
        { label: '障碍', value: trunc(c.obstacle, 20) },
      ];
    case 'CONFLICT':
      return [
        { label: '类型', value: c.conflict_type || '?' },
        { label: '根源', value: trunc(c.root_cause, 25) },
      ];
    case 'TURNING_POINT':
      return [
        { label: '类型', value: c.turning_type || '?' },
        { label: '前', value: trunc(c.before_state, 20) },
        { label: '后', value: trunc(c.after_state, 20) },
      ];
    case 'HOOK':
      return [
        { label: '类型', value: c.hook_type || '?' },
        { label: '埋设', value: `第${c.plant_chapter || '?'}章` },
        { label: '回收', value: `第${c.payoff_chapter || '?'}章` },
      ];
    case 'FORESHADOW':
      return [
        { label: '暗示', value: trunc(c.hint_content, 30) },
        { label: '回收', value: `第${c.payoff_chapter || '?'}章` },
      ];
    case 'SURPRISE':
      return [
        { label: '类型', value: c.surprise_type || '?' },
        { label: '揭示', value: trunc(c.revelation, 25) },
      ];
    // ─── 关系类 ────────────────────────────────
    case 'RELATIONSHIP':
      return [
        { label: '角色', value: `${c.party_a_id || '?'} ↔ ${c.party_b_id || '?'}` },
        { label: '强度', value: c.intensity ? `${c.intensity}/10` : '?' },
      ];
    case 'FACTION_RELATION':
      return [
        { label: '势力', value: `${c.faction_a_id || '?'} ↔ ${c.faction_b_id || '?'}` },
        { label: '紧张度', value: c.current_tension ? `${c.current_tension}/10` : '?' },
      ];
    // ─── 表达类 ────────────────────────────────
    case 'ATMOSPHERE':
      return [
        { label: '基调', value: c.emotional_tone || '?' },
        { label: '细节', value: trunc(c.sensory_details, 25) },
      ];
    case 'EMOTION_TARGET':
      return [
        { label: '情绪', value: c.primary_emotion || '?' },
        { label: '强度', value: c.intensity ? `${c.intensity}/10` : '?' },
      ];
    case 'RHYTHM':
      return [
        { label: '节奏', value: c.rhythm_type || '?' },
        { label: '说明', value: trunc(c.pacing_notes, 25) },
      ];
    case 'THEME_STATEMENT':
      return [
        { label: '主题', value: trunc(c.theme, 35) },
      ];
    case 'LENS':
      return [
        { label: '镜头', value: c.lens_type || '?' },
        { label: '焦点', value: trunc(c.focus_description, 25) },
      ];
    // ─── 剧本类 ────────────────────────────────
    case 'SCENE_HEADING':
      return [
        { label: '地点', value: c.location || '?' },
        { label: '时间', value: c.time_of_day || '?' },
      ];
    case 'ACTION_LINE':
      return [
        { label: '动作', value: trunc(c.description, 35) },
      ];
    case 'DIALOGUE':
      return [
        { label: c.character_id || '角色', value: trunc(c.line_text, 35) },
      ];
    case 'VISUAL_MOTIF':
      return [
        { label: '象征', value: trunc(c.symbolic_meaning, 30) },
        { label: '描述', value: trunc(c.visual_description, 25) },
      ];
    // ─── 大纲类（参考 Dramatica-Flow 叙事架构） ────
    case 'STORY_SYNOPSIS':
      return [
        { label: '梗概', value: trunc(c.logline, 35) },
        { label: '基调', value: c.tone ? trunc(c.tone, 20) : undefined },
        { label: '主题', value: c.theme ? trunc(c.theme, 25) : undefined },
      ].filter(r => r.value);
    case 'STORY_OUTLINE':
      return [
        { label: '梗概', value: trunc(c.logline, 35) },
        { label: '第一幕', value: trunc(c.act1_summary, 25) },
        { label: c.ending_type || '结局', value: trunc(c.climax_design || c.act3_summary, 25) },
      ];
    case 'CHAPTER_OUTLINE':
      return [
        { label: c.dramatic_function || '叙事', value: trunc(c.summary, 35) },
        { label: '节拍', value: trunc(c.beat1_desc || c.beat2_desc, 30) },
        { label: '视角', value: c.pov_character || '?' },
      ];
    case 'CHAPTER_DETAIL':
      return [
        { label: '场景1', value: c.scene1_heading ? `${c.scene1_heading}${c.scene1_content ? ': ' + trunc(c.scene1_content, 20) : ''}` : '-' },
        { label: '场景2', value: c.scene2_heading ? `${c.scene2_heading}${c.scene2_content ? ': ' + trunc(c.scene2_content, 20) : ''}` : '-' },
        { label: '冲突', value: trunc(c.key_conflicts, 25) },
      ];
    // ─── 特殊类 ────────────────────────────────
    case 'STORY_CARD':
      return [
        { label: '分类', value: c.genre || '?' },
        { label: '风格', value: trunc(c.writing_modifier, 25) },
      ];
    case 'READER_EMOTION_CURVE':
      return [
        { label: '走向', value: c.overall_trajectory || '?' },
        { label: '高峰', value: trunc(c.peak_points, 25) },
      ];
    default:
      return [];
  }
}

function trunc(text: string, max: number): string {
  if (!text) return '';
  return text.length > max ? text.substring(0, max) + '…' : text;
}

const BaseBlock: React.FC<NodeProps<BlockData>> = ({ data, selected }) => {
  const color = data.color || BLOCK_COLORS[data.type] || '#999';
  const completeness = data.completeness || 0;
  const title = getBlockTitle(data);
  const summary = getBlockSummary(data);
  const tooltip = `${BLOCK_LABELS[data.type] || data.type} | 完整度: ${Math.round(completeness * 100)}% | ${title}`;

  return (
    <div
      className={`block-node ${selected ? 'selected' : ''} ${data.is_draft ? 'draft-block' : ''}`}
      style={{ borderColor: color }}
      title={tooltip}
    >
      <div className="block-header">
        <div className="block-type-icon" style={{ background: color }} title={BLOCK_LABELS[data.type] || data.type}>
          {BLOCK_ICONS[data.type] || '?'}
        </div>
        <div className="block-title">{title}</div>
        <div className="block-completeness">
          <div
            className="block-completeness-fill"
            style={{
              height: `${completeness * 100}%`,
              background: completeness > 0.6 ? '#50C878' : completeness > 0.3 ? '#F39C12' : '#E74C3C',
            }}
          />
        </div>
      </div>
      {!data.collapsed && summary.length > 0 && (
        <div className="block-content-preview">
          {summary.map((item, i) => (
            <div key={i} style={{ display: 'flex', gap: 4, lineHeight: 1.6 }}>
              <span style={{ color: color, opacity: 0.7, flexShrink: 0, fontSize: 10 }}>{item.label}:</span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.value || '?'}</span>
            </div>
          ))}
        </div>
      )}
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
};

export default BaseBlock;
