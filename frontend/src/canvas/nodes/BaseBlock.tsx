import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { BlockData, BLOCK_COLORS } from '../../types/blocks';
import { t } from '../../i18n';

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
  STORYBOARD: '🎬',
};

function getBlockTitle(data: BlockData): string {
  const c = data.content || {};
  if (data.type === 'CHARACTER') return c.name || t('char.new_character');
  if (data.type === 'SCENE') return c.title || t('block.new_scene');
  if (data.type === 'TIMELINE') return c.timeline_name || t('block.new_timeline');
  if (data.type === 'EVENT') return c.title || t('block.new_event');
  if (data.type === 'HOOK') return c.title || t('block.new_hook');
  if (data.type === 'WORLDVIEW') return c.world_name || t('block.new_worldview');
  if (data.type === 'FACTION') return c.name || t('block.new_faction');
  if (data.type === 'GOAL') return c.surface_goal || t('block.new_goal');
  if (data.type === 'CONFLICT') return c.title || t('block.new_conflict');
  if (data.type === 'TURNING_POINT') return c.title || t('block.new_turning');
  if (data.type === 'FORESHADOW') return c.title || t('block.new_foreshadow');
  if (data.type === 'SURPRISE') return c.title || t('block.new_surprise');
  if (data.type === 'RELATIONSHIP') return c.relationship_type || t('block.new_relationship');
  if (data.type === 'FACTION_RELATION') return c.relation_type || t('block.faction_relation');
  if (data.type === 'ATMOSPHERE') return c.name || t('block.new_atmosphere');
  if (data.type === 'RULE_CONSTRAINT') return c.rule_name || t('block.new_rule');
  if (data.type === 'WORLD_DEVELOPMENT') return c.aspect || t('block.world_development');
  if (data.type === 'VISUAL_MOTIF') return c.motif_name || t('block.visual_motif');
  if (data.type === 'LENS') return c.lens_type || t('block.lens');
  if (data.type === 'SCENE_HEADING') return [c.interior_exterior, c.location, c.time_of_day].filter(Boolean).join(' ') || t('block.scene_heading');
  if (data.type === 'ACTION_LINE') return (c.description || '').substring(0, 30) || t('block.action_line');
  if (data.type === 'DIALOGUE') return (c.line_text || '').substring(0, 30) || t('block.dialogue');
  if (data.type === 'STORY_CARD') return c.card_name || c.card_id || t('block.story_card');
  if (data.type === 'READER_EMOTION_CURVE') return `${c.overall_trajectory || t('block.curve')}`;
  if (data.type === 'THEME_STATEMENT') return (c.theme || '').substring(0, 30) || t('block.theme_statement');
  if (data.type === 'EMOTION_TARGET') return `${t('field.chapter')}${c.chapter || '?'} ${c.primary_emotion || ''}`;
  if (data.type === 'RHYTHM') return `${t('field.chapter')}${c.chapter || '?'} ${c.rhythm_type || ''}`;
  if (data.type === 'CURRENT_STATE') return c.character_id ? `${t('field.character_id')}${c.character_id} ${t('field.chapter')}${c.chapter || '?'}` : t('block.current_state');
  if (data.type === 'INFORMATION_BOUNDARY') return c.character_id ? `${t('field.character_id')}${c.character_id} ${t('field.chapter')}${c.chapter || '?'}` : t('block.information_boundary');
  if (data.type === 'TIMESTAMP') return c.era_name || t('block.new_timestamp');
  if (data.type === 'STORY_OUTLINE') return c.title || t('block.story_outline');
  if (data.type === 'CHAPTER_OUTLINE') return `${t('field.chapter')}${c.chapter_number || '?'} ${c.title || t('block.outline')}`;
  if (data.type === 'CHAPTER_DETAIL') return `${t('field.chapter')}${c.chapter_number || '?'}${t('block.detail')}: ${c.title || ''}`;
  if (data.type === 'STORY_SYNOPSIS') return c.title || t('block.story_synopsis');
  if (data.type === 'STORYBOARD') return `${t('field.chapter')}${c.chapter_number || '?'} ${c.title || t('block.STORYBOARD')}`;
  return t(`block.${data.type}`);
}

/**
 * 按块类型返回要在画布块上显示的关键字段信息（最多3行）
 */
function getBlockSummary(data: BlockData): { label: string; value: string | undefined }[] {
  const c = data.content || {};

  switch (data.type) {
    // ─── 角色类 ────────────────────────────────
    case 'PERSONALITY':
      return [
        { label: t('summary.function'), value: c.dramatica_function || '?' },
        { label: t('summary.values'), value: trunc(c.core_values, 28) },
      ];
    case 'GROWTH':
      return [
        { label: t('summary.arc'), value: c.arc_type || '?' },
        { label: t('summary.end_point'), value: trunc(c.end_state, 28) },
      ];
    case 'BACKSTORY':
      return [
        { label: t('summary.origin'), value: trunc(c.origin, 30) },
        { label: t('summary.secrets'), value: trunc(c.secrets, 20) },
      ];
    case 'CURRENT_STATE':
      return [
        { label: t('summary.psychology'), value: trunc(c.psychological_condition, 30) },
        { label: t('summary.emotion'), value: trunc(c.emotional_state, 20) },
      ];
    case 'INFORMATION_BOUNDARY':
      return [
        { label: t('summary.known'), value: trunc(c.confirmed_knowledge, 30) },
        { label: t('summary.misbelief'), value: trunc(c.wrongly_believes, 20) },
      ];
    case 'OMNISCIENT_LAYER':
      return [
        { label: t('summary.facts'), value: trunc(c.true_facts, 30) },
      ];
    // ─── 世界类 ────────────────────────────────
    case 'WORLDVIEW':
      return [
        { label: t('summary.rules'), value: trunc(c.fundamental_rules, 30) },
      ];
    case 'FACTION':
      return [
        { label: t('summary.creed'), value: trunc(c.ideology, 30) },
      ];
    case 'RULE_CONSTRAINT':
      return [
        { label: t('summary.type'), value: c.rule_type || '?' },
        { label: t('summary.mechanism'), value: trunc(c.mechanism, 25) },
      ];
    case 'WORLD_DEVELOPMENT':
      return [
        { label: t('summary.current'), value: trunc(c.current_state, 30) },
      ];
    case 'TIMESTAMP':
      return [
        { label: t('summary.range'), value: c.time_range || '?' },
        { label: t('summary.changes'), value: trunc(c.key_changes, 25) },
      ];
    // ─── 叙事结构类 ────────────────────────────
    case 'TIMELINE':
      return [
        { label: t('summary.type'), value: c.timeline_type || '?' },
        { label: t('summary.pov'), value: trunc(c.pov_characters, 25) },
      ];
    case 'EVENT':
      return [
        { label: t('summary.content'), value: trunc(c.what_happens, 35) },
      ];
    case 'GOAL':
      return [
        { label: t('summary.deep_goal'), value: trunc(c.deep_goal, 30) },
        { label: t('summary.obstacle'), value: trunc(c.obstacle, 20) },
      ];
    case 'CONFLICT':
      return [
        { label: t('summary.type'), value: c.conflict_type || '?' },
        { label: t('summary.root'), value: trunc(c.root_cause, 25) },
      ];
    case 'TURNING_POINT':
      return [
        { label: t('summary.type'), value: c.turning_type || '?' },
        { label: t('summary.before'), value: trunc(c.before_state, 20) },
        { label: t('summary.after'), value: trunc(c.after_state, 20) },
      ];
    case 'HOOK':
      return [
        { label: t('summary.type'), value: c.hook_type || '?' },
        { label: t('summary.plant'), value: `${t('field.chapter')}${c.plant_chapter || '?'}` },
        { label: t('summary.payoff'), value: `${t('field.chapter')}${c.payoff_chapter || '?'}` },
      ];
    case 'FORESHADOW':
      return [
        { label: t('summary.hint'), value: trunc(c.hint_content, 30) },
        { label: t('summary.payoff'), value: `${t('field.chapter')}${c.payoff_chapter || '?'}` },
      ];
    case 'SURPRISE':
      return [
        { label: t('summary.type'), value: c.surprise_type || '?' },
        { label: t('summary.reveal'), value: trunc(c.revelation, 25) },
      ];
    // ─── 关系类 ────────────────────────────────
    case 'RELATIONSHIP':
      return [
        { label: t('summary.character'), value: `${c.party_a_id || '?'} ↔ ${c.party_b_id || '?'}` },
        { label: t('summary.intensity'), value: c.intensity ? `${c.intensity}/10` : '?' },
      ];
    case 'FACTION_RELATION':
      return [
        { label: t('summary.faction'), value: `${c.faction_a_id || '?'} ↔ ${c.faction_b_id || '?'}` },
        { label: t('summary.tension'), value: c.current_tension ? `${c.current_tension}/10` : '?' },
      ];
    // ─── 表达类 ────────────────────────────────
    case 'ATMOSPHERE':
      return [
        { label: t('summary.tone'), value: c.emotional_tone || '?' },
        { label: t('summary.details'), value: trunc(c.sensory_details, 25) },
      ];
    case 'EMOTION_TARGET':
      return [
        { label: t('summary.emotion'), value: c.primary_emotion || '?' },
        { label: t('summary.intensity'), value: c.intensity ? `${c.intensity}/10` : '?' },
      ];
    case 'RHYTHM':
      return [
        { label: t('summary.rhythm'), value: c.rhythm_type || '?' },
        { label: t('summary.notes'), value: trunc(c.pacing_notes, 25) },
      ];
    case 'THEME_STATEMENT':
      return [
        { label: t('summary.theme'), value: trunc(c.theme, 35) },
      ];
    case 'LENS':
      return [
        { label: t('summary.lens'), value: c.lens_type || '?' },
        { label: t('summary.focus'), value: trunc(c.focus_description, 25) },
      ];
    // ─── 剧本类 ────────────────────────────────
    case 'SCENE_HEADING':
      return [
        { label: t('summary.location'), value: c.location || '?' },
        { label: t('summary.time'), value: c.time_of_day || '?' },
      ];
    case 'ACTION_LINE':
      return [
        { label: t('summary.action'), value: trunc(c.description, 35) },
      ];
    case 'DIALOGUE':
      return [
        { label: c.character_id || t('summary.character'), value: trunc(c.line_text, 35) },
      ];
    case 'VISUAL_MOTIF':
      return [
        { label: t('summary.symbol'), value: trunc(c.symbolic_meaning, 30) },
        { label: t('summary.description'), value: trunc(c.visual_description, 25) },
      ];
    // ─── 大纲类（参考 Dramatica-Flow 叙事架构） ────
    case 'STORY_SYNOPSIS':
      return [
        { label: t('summary.logline'), value: trunc(c.logline, 35) },
        { label: t('summary.tone'), value: c.tone ? trunc(c.tone, 20) : undefined },
        { label: t('summary.theme'), value: c.theme ? trunc(c.theme, 25) : undefined },
      ].filter(r => r.value);
    case 'STORY_OUTLINE':
      return [
        { label: t('summary.logline'), value: trunc(c.logline, 35) },
        { label: t('summary.act1'), value: trunc(c.act1_summary, 25) },
        { label: c.ending_type || t('summary.ending'), value: trunc(c.climax_design || c.act3_summary, 25) },
      ];
    case 'CHAPTER_OUTLINE':
      return [
        { label: c.dramatic_function || t('summary.narrative'), value: trunc(c.summary, 35) },
        { label: t('summary.beat'), value: trunc(c.beat1_desc || c.beat2_desc, 30) },
        { label: t('summary.pov'), value: c.pov_character || '?' },
      ];
    case 'CHAPTER_DETAIL':
      return [
        { label: t('summary.scene1'), value: c.scene1_heading ? `${c.scene1_heading}${c.scene1_content ? ': ' + trunc(c.scene1_content, 20) : ''}` : '-' },
        { label: t('summary.scene2'), value: c.scene2_heading ? `${c.scene2_heading}${c.scene2_content ? ': ' + trunc(c.scene2_content, 20) : ''}` : '-' },
        { label: t('summary.conflict'), value: trunc(c.key_conflicts, 25) },
      ];
    // ─── 特殊类 ────────────────────────────────
    case 'STORY_CARD':
      return [
        { label: t('summary.genre'), value: c.genre || '?' },
        { label: t('summary.style'), value: trunc(c.writing_modifier, 25) },
      ];
    case 'READER_EMOTION_CURVE':
      return [
        { label: t('summary.trajectory'), value: c.overall_trajectory || '?' },
        { label: t('summary.peak'), value: trunc(c.peak_points, 25) },
      ];
    case 'STORYBOARD':
      return [
        { label: t('field.total_shots'), value: c.total_shots ? `${c.total_shots}` : '?' },
        { label: t('field.visual_style'), value: trunc(c.visual_style, 25) },
        { label: t('field.estimated_duration'), value: c.estimated_duration || '?' },
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
  const tooltip = `${t(`block.${data.type}`)} | ${t('editor.completeness')}: ${Math.round(completeness * 100)}% | ${title}`;

  return (
    <div
      className={`block-node ${selected ? 'selected' : ''} ${data.is_draft ? 'draft-block' : ''}`}
      style={{ borderColor: color }}
      title={tooltip}
    >
      <div className="block-header">
        <div className="block-type-icon" style={{ background: color }} title={t(`block.${data.type}`)}>
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
