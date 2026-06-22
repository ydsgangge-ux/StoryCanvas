import React, { useState, useEffect } from 'react';
import { useCanvasStore } from '../store/canvasStore';
import { useProjectStore } from '../store/projectStore';
import { useUIStore } from '../store/uiStore';
import { BlockData, BlockType, BLOCK_COLORS } from '../types/blocks';
import { useT } from '../i18n/useT';

const FIELD_GROUPS: Record<string, { key: string; labelKey: string; type: 'text' | 'textarea' | 'number' | 'select'; optionKeys?: string[] }[]> = {
  CHARACTER: [
    { key: 'name', labelKey: 'field.name', type: 'text' },
    { key: 'want', labelKey: 'field.want', type: 'textarea' },
    { key: 'need', labelKey: 'field.need', type: 'textarea' },
    { key: 'fatal_flaw', labelKey: 'field.fatal_flaw', type: 'textarea' },
    { key: 'surface_personality', labelKey: 'field.surface_personality', type: 'textarea' },
    { key: 'role_archetype', labelKey: 'field.role_archetype', type: 'text' },
    { key: 'superpower', labelKey: 'field.superpower', type: 'textarea' },
    { key: 'voice_style', labelKey: 'field.voice_style', type: 'textarea' },
    { key: 'appearance', labelKey: 'field.appearance', type: 'textarea' },
    { key: 'age', labelKey: 'field.age', type: 'text' },
  ],
  PERSONALITY: [
    { key: 'character_id', labelKey: 'field.character_id', type: 'text' },
    { key: 'core_values', labelKey: 'field.core_values', type: 'textarea' },
    { key: 'behavior_patterns', labelKey: 'field.behavior_patterns', type: 'textarea' },
    { key: 'dramatica_function', labelKey: 'field.dramatica_function', type: 'select', optionKeys: ['option.protagonist', 'option.influence_character', 'option.emotion_judgment', 'option.rational_thinking'] },
  ],
  GROWTH: [
    { key: 'character_id', labelKey: 'field.character_id', type: 'text' },
    { key: 'arc_type', labelKey: 'field.arc_type', type: 'select', optionKeys: ['option.positive_growth', 'option.fall', 'option.redemption', 'option.disillusionment', 'option.transformation'] },
    { key: 'start_state', labelKey: 'field.start_state', type: 'textarea' },
    { key: 'end_state', labelKey: 'field.end_state', type: 'textarea' },
    { key: 'keystone_moments', labelKey: 'field.keystone_moments', type: 'textarea' },
  ],
  BACKSTORY: [
    { key: 'character_id', labelKey: 'field.character_id', type: 'text' },
    { key: 'origin', labelKey: 'field.origin', type: 'textarea' },
    { key: 'formative_events', labelKey: 'field.formative_events', type: 'textarea' },
    { key: 'secrets', labelKey: 'field.secrets', type: 'textarea' },
  ],
  CURRENT_STATE: [
    { key: 'character_id', labelKey: 'field.character_id', type: 'text' },
    { key: 'chapter', labelKey: 'field.chapter', type: 'number' },
    { key: 'physical_condition', labelKey: 'field.physical_condition', type: 'textarea' },
    { key: 'psychological_condition', labelKey: 'field.psychological_condition', type: 'textarea' },
    { key: 'active_goals', labelKey: 'field.active_goals', type: 'textarea' },
    { key: 'emotional_state', labelKey: 'field.emotional_state', type: 'textarea' },
  ],
  INFORMATION_BOUNDARY: [
    { key: 'character_id', labelKey: 'field.character_id', type: 'text' },
    { key: 'chapter', labelKey: 'field.chapter', type: 'number' },
    { key: 'confirmed_knowledge', labelKey: 'field.confirmed_knowledge', type: 'textarea' },
    { key: 'wrongly_believes', labelKey: 'field.wrongly_believes', type: 'textarea' },
    { key: 'dramatic_irony', labelKey: 'field.dramatic_irony', type: 'textarea' },
  ],
  OMNISCIENT_LAYER: [
    { key: 'true_facts', labelKey: 'field.true_facts', type: 'textarea' },
    { key: 'reader_reveal_plan', labelKey: 'field.reader_reveal_plan', type: 'textarea' },
  ],
  WORLDVIEW: [
    { key: 'world_name', labelKey: 'field.world_name', type: 'text' },
    { key: 'fundamental_rules', labelKey: 'field.fundamental_rules', type: 'textarea' },
    { key: 'cosmology', labelKey: 'field.cosmology', type: 'textarea' },
    { key: 'power_system', labelKey: 'field.power_system', type: 'textarea' },
    { key: 'tone', labelKey: 'field.tone', type: 'text' },
  ],
  FACTION: [
    { key: 'name', labelKey: 'field.name', type: 'text' },
    { key: 'ideology', labelKey: 'field.ideology', type: 'textarea' },
    { key: 'goal', labelKey: 'field.goal', type: 'textarea' },
    { key: 'resources', labelKey: 'field.resources', type: 'textarea' },
    { key: 'weakness', labelKey: 'field.weakness', type: 'textarea' },
  ],
  RULE_CONSTRAINT: [
    { key: 'rule_name', labelKey: 'field.rule_name', type: 'text' },
    { key: 'rule_type', labelKey: 'field.rule_type', type: 'select', optionKeys: ['option.physical_law', 'option.social_rule', 'option.magic_rule', 'option.taboo', 'option.tech_limit'] },
    { key: 'mechanism', labelKey: 'field.mechanism', type: 'textarea' },
    { key: 'consequence_of_breaking', labelKey: 'field.consequence_of_breaking', type: 'textarea' },
  ],
  WORLD_DEVELOPMENT: [
    { key: 'aspect', labelKey: 'field.aspect', type: 'text' },
    { key: 'current_state', labelKey: 'field.current_state', type: 'textarea' },
    { key: 'trajectory', labelKey: 'field.trajectory', type: 'textarea' },
    { key: 'key_events', labelKey: 'field.key_events', type: 'textarea' },
  ],
  TIMESTAMP: [
    { key: 'era_name', labelKey: 'field.era_name', type: 'text' },
    { key: 'time_range', labelKey: 'field.time_range', type: 'text' },
    { key: 'key_changes', labelKey: 'field.key_changes', type: 'textarea' },
  ],
  TIMELINE: [
    { key: 'timeline_name', labelKey: 'field.timeline_name', type: 'text' },
    { key: 'timeline_type', labelKey: 'field.rule_type', type: 'select', optionKeys: ['option.main_line', 'option.sub_line', 'option.flashback_line', 'option.parallel_line'] },
    { key: 'pov_characters', labelKey: 'field.pov_characters', type: 'textarea' },
  ],
  SCENE: [
    { key: 'title', labelKey: 'field.title', type: 'text' },
    { key: 'scene_goal', labelKey: 'field.scene_goal', type: 'textarea' },
    { key: 'emotion_target', labelKey: 'field.emotion_target', type: 'textarea' },
    { key: 'tension_level', labelKey: 'field.tension_level', type: 'number' },
    { key: 'scene_type', labelKey: 'field.scene_type', type: 'text' },
    { key: 'what_happens', labelKey: 'field.what_happens', type: 'textarea' },
    { key: 'characters_present', labelKey: 'field.characters_present', type: 'textarea' },
  ],
  EVENT: [
    { key: 'title', labelKey: 'field.title', type: 'text' },
    { key: 'what_happens', labelKey: 'field.what_happened', type: 'textarea' },
    { key: 'event_type', labelKey: 'field.event_type', type: 'text' },
    { key: 'immediate_effects', labelKey: 'field.immediate_effects', type: 'textarea' },
  ],
  GOAL: [
    { key: 'surface_goal', labelKey: 'field.surface_goal', type: 'textarea' },
    { key: 'deep_goal', labelKey: 'field.deep_goal', type: 'textarea' },
    { key: 'obstacle', labelKey: 'field.obstacle', type: 'textarea' },
    { key: 'stakes', labelKey: 'field.stakes', type: 'textarea' },
  ],
  CONFLICT: [
    { key: 'title', labelKey: 'field.title', type: 'text' },
    { key: 'conflict_type', labelKey: 'field.conflict_type', type: 'select', optionKeys: ['option.person_vs_person', 'option.person_vs_nature', 'option.person_vs_society', 'option.person_vs_self', 'option.person_vs_fate', 'option.person_vs_tech'] },
    { key: 'root_cause', labelKey: 'field.root_cause', type: 'textarea' },
    { key: 'surface_manifestation', labelKey: 'field.surface_manifestation', type: 'textarea' },
    { key: 'resolution_type', labelKey: 'field.resolution_type', type: 'select', optionKeys: ['option.compromise', 'option.victory', 'option.defeat', 'option.coexistence', 'option.sublimation'] },
  ],
  TURNING_POINT: [
    { key: 'title', labelKey: 'field.title', type: 'text' },
    { key: 'turning_type', labelKey: 'field.turning_type', type: 'select', optionKeys: ['option.crisis', 'option.discovery', 'option.betrayal', 'option.sacrifice', 'option.awakening', 'option.reunion'] },
    { key: 'before_state', labelKey: 'field.before_state', type: 'textarea' },
    { key: 'trigger', labelKey: 'field.trigger', type: 'textarea' },
    { key: 'after_state', labelKey: 'field.after_state', type: 'textarea' },
  ],
  HOOK: [
    { key: 'title', labelKey: 'field.title', type: 'text' },
    { key: 'hook_type', labelKey: 'field.hook_type', type: 'select', optionKeys: ['option.identity_hook', 'option.fate_hook', 'option.truth_hook', 'option.moral_dilemma', 'option.time_bomb'] },
    { key: 'content_planted', labelKey: 'field.content_planted', type: 'textarea' },
    { key: 'plant_chapter', labelKey: 'field.plant_chapter', type: 'text' },
    { key: 'payoff_chapter', labelKey: 'field.payoff_chapter', type: 'text' },
    { key: 'content_resolved', labelKey: 'field.content_resolved', type: 'textarea' },
  ],
  FORESHADOW: [
    { key: 'title', labelKey: 'field.title', type: 'text' },
    { key: 'hint_content', labelKey: 'field.hint_content', type: 'textarea' },
    { key: 'plant_chapter', labelKey: 'field.plant_chapter', type: 'text' },
    { key: 'payoff_chapter', labelKey: 'field.payoff_chapter', type: 'text' },
    { key: 'payoff_content', labelKey: 'field.payoff_content', type: 'textarea' },
  ],
  SURPRISE: [
    { key: 'title', labelKey: 'field.title', type: 'text' },
    { key: 'surprise_type', labelKey: 'field.surprise_type', type: 'select', optionKeys: ['option.identity_reveal', 'option.truth_reversal', 'option.fate_reversal', 'option.relationship_reveal', 'option.worldview_overturn'] },
    { key: 'revelation', labelKey: 'field.revelation', type: 'textarea' },
    { key: 'setup_required', labelKey: 'field.setup_required', type: 'textarea' },
  ],
  RELATIONSHIP: [
    { key: 'party_a_id', labelKey: 'field.party_a_id', type: 'text' },
    { key: 'party_b_id', labelKey: 'field.party_b_id', type: 'text' },
    { key: 'relationship_type', labelKey: 'field.relationship_type', type: 'select', optionKeys: ['option.ally', 'option.rival', 'option.lover', 'option.mentor', 'option.family', 'option.hierarchy', 'option.secret_enemy'] },
    { key: 'dynamic', labelKey: 'field.dynamic', type: 'textarea' },
    { key: 'history', labelKey: 'field.history', type: 'textarea' },
    { key: 'intensity', labelKey: 'field.intensity', type: 'number' },
  ],
  FACTION_RELATION: [
    { key: 'faction_a_id', labelKey: 'field.faction_a_id', type: 'text' },
    { key: 'faction_b_id', labelKey: 'field.faction_b_id', type: 'text' },
    { key: 'relation_type', labelKey: 'field.relation_type', type: 'select', optionKeys: ['option.alliance', 'option.hostile', 'option.cold_war', 'option.trade', 'option.vassal', 'option.secret_coop'] },
    { key: 'key_events', labelKey: 'field.key_events', type: 'textarea' },
    { key: 'current_tension', labelKey: 'field.current_tension', type: 'number' },
  ],
  ATMOSPHERE: [
    { key: 'name', labelKey: 'field.atmosphere_name', type: 'text' },
    { key: 'sensory_details', labelKey: 'field.sensory_details', type: 'textarea' },
    { key: 'emotional_tone', labelKey: 'field.emotional_tone', type: 'text' },
    { key: 'associated_elements', labelKey: 'field.associated_elements', type: 'textarea' },
  ],
  EMOTION_TARGET: [
    { key: 'chapter', labelKey: 'field.chapter', type: 'number' },
    { key: 'primary_emotion', labelKey: 'field.primary_emotion', type: 'select', optionKeys: ['option.tension', 'option.sadness', 'option.joy', 'option.fear', 'option.anger', 'option.warmth', 'option.shock', 'option.confusion'] },
    { key: 'intensity', labelKey: 'field.intensity', type: 'number' },
    { key: 'trigger', labelKey: 'field.trigger_reason', type: 'textarea' },
    { key: 'resolution', labelKey: 'field.resolution', type: 'textarea' },
  ],
  RHYTHM: [
    { key: 'chapter', labelKey: 'field.chapter', type: 'number' },
    { key: 'rhythm_type', labelKey: 'field.rhythm_type', type: 'select', optionKeys: ['option.accelerate', 'option.decelerate', 'option.sudden_turn', 'option.steady', 'option.climax', 'option.settle'] },
    { key: 'pacing_notes', labelKey: 'field.pacing_notes', type: 'textarea' },
    { key: 'transition_style', labelKey: 'field.transition_style', type: 'text' },
  ],
  THEME_STATEMENT: [
    { key: 'theme', labelKey: 'field.theme', type: 'textarea' },
    { key: 'exploration_approach', labelKey: 'field.exploration_approach', type: 'textarea' },
    { key: 'counter_argument', labelKey: 'field.counter_argument', type: 'textarea' },
  ],
  LENS: [
    { key: 'lens_type', labelKey: 'field.lens_type', type: 'select', optionKeys: ['option.close_up', 'option.wide_shot', 'option.bird_eye', 'option.following', 'option.montage', 'option.subjective'] },
    { key: 'focus_description', labelKey: 'field.focus_description', type: 'textarea' },
    { key: 'application_notes', labelKey: 'field.application_notes', type: 'textarea' },
  ],
  SCENE_HEADING: [
    { key: 'interior_exterior', labelKey: 'field.interior_exterior', type: 'select', optionKeys: ['option.interior', 'option.exterior', 'option.both_inout'] },
    { key: 'location', labelKey: 'field.location', type: 'text' },
    { key: 'time_of_day', labelKey: 'field.time_of_day', type: 'select', optionKeys: ['option.day', 'option.night', 'option.morning', 'option.dusk', 'option.continued'] },
  ],
  ACTION_LINE: [
    { key: 'character_id', labelKey: 'field.character_id', type: 'text' },
    { key: 'description', labelKey: 'field.description', type: 'textarea' },
    { key: 'continuation_note', labelKey: 'field.continuation_note', type: 'textarea' },
  ],
  DIALOGUE: [
    { key: 'character_id', labelKey: 'field.character_id', type: 'text' },
    { key: 'parenthetical', labelKey: 'field.parenthetical', type: 'text' },
    { key: 'line_text', labelKey: 'field.line_text', type: 'textarea' },
    { key: 'delivery_note', labelKey: 'field.delivery_note', type: 'textarea' },
  ],
  VISUAL_MOTIF: [
    { key: 'motif_name', labelKey: 'field.motif_name', type: 'text' },
    { key: 'visual_description', labelKey: 'field.visual_description', type: 'textarea' },
    { key: 'symbolic_meaning', labelKey: 'field.symbolic_meaning', type: 'textarea' },
  ],
  STORY_SYNOPSIS: [
    { key: 'title', labelKey: 'field.story_title', type: 'text' },
    { key: 'logline', labelKey: 'field.logline', type: 'textarea' },
    { key: 'synopsis', labelKey: 'field.synopsis', type: 'textarea' },
    { key: 'genre', labelKey: 'field.genre', type: 'text' },
    { key: 'theme', labelKey: 'field.theme', type: 'textarea' },
    { key: 'tone', labelKey: 'field.tone', type: 'textarea' },
    { key: 'protagonists', labelKey: 'field.protagonists', type: 'textarea' },
    { key: 'antagonists', labelKey: 'field.antagonists', type: 'textarea' },
    { key: 'setting', labelKey: 'field.setting', type: 'textarea' },
  ],
  STORY_OUTLINE: [
    { key: 'title', labelKey: 'field.story_title', type: 'text' },
    { key: 'logline', labelKey: 'field.logline', type: 'textarea' },
    { key: 'genre', labelKey: 'field.genre', type: 'text' },
    { key: 'divider_acts', labelKey: 'field.divider_acts', type: 'text' },
    { key: 'act1_summary', labelKey: 'field.act1_summary', type: 'textarea' },
    { key: 'act2_summary', labelKey: 'field.act2_summary', type: 'textarea' },
    { key: 'act3_summary', labelKey: 'field.act3_summary', type: 'textarea' },
    { key: 'divider_structure', labelKey: 'field.divider_structure', type: 'text' },
    { key: 'key_turning_points', labelKey: 'field.key_turning_points', type: 'textarea' },
    { key: 'central_conflict', labelKey: 'field.central_conflict', type: 'textarea' },
    { key: 'climax_design', labelKey: 'field.climax_design', type: 'textarea' },
    { key: 'ending_type', labelKey: 'field.ending_type', type: 'select', optionKeys: ['option.happy_ending', 'option.tragic_ending', 'option.open_ending', 'option.twist_ending', 'option.ambiguous_ending'] },
    { key: 'emotional_roadmap', labelKey: 'field.emotional_roadmap', type: 'textarea' },
  ],
  CHAPTER_OUTLINE: [
    { key: 'chapter_number', labelKey: 'field.chapter_number', type: 'number' },
    { key: 'title', labelKey: 'field.chapter_title', type: 'text' },
    { key: 'summary', labelKey: 'field.summary', type: 'textarea' },
    { key: 'narrative_goal', labelKey: 'field.narrative_goal', type: 'textarea' },
    { key: 'dramatic_function', labelKey: 'field.dramatic_function', type: 'select', optionKeys: ['option.setup', 'option.inciting', 'option.turning', 'option.midpoint', 'option.crisis_func', 'option.climax_func', 'option.revelation', 'option.choice', 'option.consequence', 'option.transition'] },
    { key: 'divider_beats', labelKey: 'field.divider_beats', type: 'text' },
    { key: 'beat1_desc', labelKey: 'field.beat1_desc', type: 'textarea' },
    { key: 'beat2_desc', labelKey: 'field.beat2_desc', type: 'textarea' },
    { key: 'beat3_desc', labelKey: 'field.beat3_desc', type: 'textarea' },
    { key: 'pov_character', labelKey: 'field.pov_character', type: 'text' },
    { key: 'target_words', labelKey: 'field.target_words', type: 'number' },
    { key: 'emotional_arc', labelKey: 'field.emotional_arc', type: 'textarea' },
    { key: 'status', labelKey: 'field.status', type: 'select', optionKeys: ['option.status_planned', 'option.status_outlined', 'option.status_generated', 'option.status_approved'] },
  ],
  CHAPTER_DETAIL: [
    { key: 'chapter_number', labelKey: 'field.chapter_number', type: 'number' },
    { key: 'title', labelKey: 'field.chapter_title', type: 'text' },
    { key: 'divider_scenes', labelKey: 'field.divider_scenes', type: 'text' },
    { key: 'scene1_heading', labelKey: 'field.scene1_heading', type: 'text' },
    { key: 'scene1_content', labelKey: 'field.scene1_content', type: 'textarea' },
    { key: 'scene2_heading', labelKey: 'field.scene2_heading', type: 'text' },
    { key: 'scene2_content', labelKey: 'field.scene2_content', type: 'textarea' },
    { key: 'scene3_heading', labelKey: 'field.scene3_heading', type: 'text' },
    { key: 'scene3_content', labelKey: 'field.scene3_content', type: 'textarea' },
    { key: 'divider_other', labelKey: 'field.divider_other', type: 'text' },
    { key: 'key_conflicts', labelKey: 'field.key_conflicts', type: 'textarea' },
    { key: 'character_goals', labelKey: 'field.character_goals', type: 'textarea' },
    { key: 'writing_notes', labelKey: 'field.writing_notes', type: 'textarea' },
  ],
  STORY_CARD: [
    { key: 'card_id', labelKey: 'field.card_id', type: 'text' },
    { key: 'card_name', labelKey: 'field.card_name', type: 'text' },
    { key: 'genre', labelKey: 'field.genre', type: 'text' },
    { key: 'writing_modifier', labelKey: 'field.writing_modifier', type: 'textarea' },
    { key: 'reference_works', labelKey: 'field.reference_works', type: 'textarea' },
  ],
  READER_EMOTION_CURVE: [
    { key: 'chapters', labelKey: 'field.chapters_covered', type: 'text' },
    { key: 'peak_points', labelKey: 'field.peak_points', type: 'textarea' },
    { key: 'valley_points', labelKey: 'field.valley_points', type: 'textarea' },
    { key: 'overall_trajectory', labelKey: 'field.overall_trajectory', type: 'select', optionKeys: ['option.increasing', 'option.decreasing', 'option.wave', 'option.rise_after_fall', 'option.fall_after_rise', 'option.flat'] },
  ],
  STORYBOARD: [
    { key: 'chapter_number', labelKey: 'field.chapter_number', type: 'number' },
    { key: 'title', labelKey: 'field.chapter_title', type: 'text' },
    { key: 'visual_style', labelKey: 'field.visual_style', type: 'text' },
    { key: 'music_suggestion', labelKey: 'field.music_suggestion', type: 'text' },
    { key: 'estimated_duration', labelKey: 'field.estimated_duration', type: 'text' },
    { key: 'total_shots', labelKey: 'field.total_shots', type: 'number' },
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
  const [generatingImageIdx, setGeneratingImageIdx] = useState<number | null>(null);
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);

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
          {t(`block.${selectedBlock.type}`)}
        <span style={{ fontSize: 11, color: '#6c6c80', marginLeft: 6 }}>({selectedBlock.type})</span>
        </span>
        <button className="btn btn-sm btn-ghost" onClick={() => useCanvasStore.getState().setSelectedBlock(null)}>
          ✕
        </button>
      </div>
      <div className="panel-body">
        <div className="block-editor">
          <div style={{ fontSize: 12, color: '#a0a0b0', marginBottom: 8 }}>
            {t('editor.completeness')}: {Math.round((selectedBlock.completeness || 0) * 100)}%
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
                {t(field.labelKey)}
              </div>
            ) : (
            <div className="field-group" key={field.key}>
              <div className="field-label">{t(field.labelKey)}</div>
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
                  <option value="">-- {t('editor.select')} --</option>
                  {(field.optionKeys || []).map((optKey) => (
                    <option key={optKey} value={optKey}>{t(optKey)}</option>
                  ))}
                </select>
              ) : field.type === 'textarea' ? (
                <textarea
                  className="form-textarea"
                  rows={3}
                  value={localContent[field.key] ?? ''}
                  onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  onBlur={handleBlur}
                  placeholder={t('editor.input_placeholder', { label: t(field.labelKey) })}
                />
              ) : (
                <input
                  className="form-input"
                  type="text"
                  value={localContent[field.key] ?? ''}
                  onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  onBlur={handleBlur}
                  placeholder={t('editor.input_placeholder', { label: t(field.labelKey) })}
                />
              )}
            </div>
            )
          ))}

          {fields.length === 0 && (
            <div style={{ color: '#6c6c80', fontSize: 13, padding: 20, textAlign: 'center' }}>
              {t('editor.no_fields')}
            </div>
          )}

          {selectedBlock.type === 'STORYBOARD' && localContent.shots && Array.isArray(localContent.shots) && (
            <div style={{ marginTop: 8, borderTop: '1px solid var(--border-color)', paddingTop: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#FF6347', marginBottom: 6 }}>
                🎬 {t('field.shots_list')} ({localContent.shots.length})
              </div>
              <div style={{ maxHeight: 500, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {localContent.shots.map((shot: any, idx: number) => (
                  <div key={idx} style={{
                    padding: '8px 10px', borderRadius: 6,
                    background: 'var(--bg-card)', border: '1px solid var(--border-color)',
                    borderLeft: '3px solid #FF6347', fontSize: 12,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontWeight: 700, color: '#FF6347' }}>
                        #{shot.shot_number || idx + 1}
                      </span>
                      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                        {/* 景别 */}
                        {shot.shot_size && (
                          <span style={{
                            fontSize: 10, padding: '1px 6px', borderRadius: 3,
                            background: 'rgba(255,99,71,0.15)', color: '#FF6347',
                          }}>
                            {shot.shot_size}
                          </span>
                        )}
                        {/* 机位角度 */}
                        {shot.camera_angle && (
                          <span style={{
                            fontSize: 10, padding: '1px 6px', borderRadius: 3,
                            background: 'rgba(52,152,219,0.15)', color: '#3498DB',
                          }} title={t('field.camera_angle')}>
                            📐 {shot.camera_angle}
                          </span>
                        )}
                        {/* 运镜方式 */}
                        {shot.camera_movement && (
                          <span style={{
                            fontSize: 10, padding: '1px 6px', borderRadius: 3,
                            background: 'rgba(26,188,156,0.15)', color: '#1ABC9C',
                          }} title={t('field.camera_movement')}>
                            🎥 {shot.camera_movement}
                          </span>
                        )}
                        <button
                          className="btn btn-sm"
                          onClick={async () => {
                            setGeneratingImageIdx(idx);
                            try {
                              const desc = shot.description || shot.notes || '';
                              const res = await fetch(`/api/projects/${currentProject.id}/generate/image`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                  prompt: desc,
                                  shot_index: idx,
                                  block_id: selectedBlock.id,
                                }),
                              });
                              if (res.ok) {
                                const data = await res.json();
                                const updated = { ...localContent };
                                updated.shots = [...updated.shots];
                                updated.shots[idx] = { ...updated.shots[idx], image: data.image_path };
                                setLocalContent(updated);
                                await updateBlock(currentProject.id, selectedBlock.id, { content: updated });
                              } else {
                                const err = await res.json();
                                alert(err.detail || t('image.generate_failed'));
                              }
                            } catch (e: any) {
                              alert(t('image.generate_error') + ': ' + e.message);
                            }
                            setGeneratingImageIdx(null);
                          }}
                          disabled={generatingImageIdx === idx}
                          style={{
                            fontSize: 10, padding: '2px 6px', borderRadius: 4,
                            background: 'linear-gradient(135deg, #9B59B6, #8E44AD)',
                            color: '#fff', border: 'none', cursor: 'pointer',
                            whiteSpace: 'nowrap',
                          }}
                          title={t('image.generate_for_shot')}
                        >
                          {generatingImageIdx === idx ? <><span className="loading-spinner" style={{ width: 10, height: 10 }} /> ...</> : '🎨'}
                        </button>
                      </div>
                    </div>
                    {/* 图片预览 */}
                    {shot.image && (
                      <div
                        style={{ marginBottom: 4, cursor: 'pointer', borderRadius: 4, overflow: 'hidden', border: '1px solid var(--border-color)' }}
                        onClick={() => setLightboxImage(shot.image)}
                        title={t('image.click_to_enlarge')}
                      >
                        <img
                          src={shot.image}
                          alt={`Shot ${shot.shot_number || idx + 1}`}
                          style={{ width: '100%', height: 80, objectFit: 'cover', display: 'block' }}
                        />
                      </div>
                    )}
                    {shot.description && (
                      <div style={{ color: '#ddd', marginBottom: 3 }}>{shot.description}</div>
                    )}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, fontSize: 10, color: '#888' }}>
                      {shot.dialogue && (
                        <span style={{ background: 'rgba(74,144,217,0.15)', color: '#4A90D9', padding: '1px 5px', borderRadius: 3 }}>
                          💬 {shot.dialogue}
                        </span>
                      )}
                      {shot.audio && (
                        <span style={{ background: 'rgba(80,200,120,0.15)', color: '#50C878', padding: '1px 5px', borderRadius: 3 }}>
                          🔊 {shot.audio}
                        </span>
                      )}
                      {shot.duration && (
                        <span style={{ background: 'rgba(243,156,18,0.15)', color: '#F39C12', padding: '1px 5px', borderRadius: 3 }}>
                          ⏱ {shot.duration}
                        </span>
                      )}
                      {shot.transition && (
                        <span style={{ background: 'rgba(155,89,182,0.15)', color: '#9B59B6', padding: '1px 5px', borderRadius: 3 }}>
                          ➡ {shot.transition}
                        </span>
                      )}
                      {shot.music_note && (
                        <span style={{ background: 'rgba(231,76,60,0.15)', color: '#E74C3C', padding: '1px 5px', borderRadius: 3 }}>
                          🎵 {shot.music_note}
                        </span>
                      )}
                    </div>
                    {shot.notes && (
                      <div style={{ fontSize: 10, color: '#999', marginTop: 3, fontStyle: 'italic' }}>
                        📝 {shot.notes}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 大图弹窗 */}
          {lightboxImage && (
            <div
              style={{
                position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                background: 'rgba(0,0,0,0.85)', zIndex: 9999,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer',
              }}
              onClick={() => setLightboxImage(null)}
            >
              <img
                src={lightboxImage}
                alt="Full size"
                style={{ maxWidth: '90vw', maxHeight: '90vh', borderRadius: 8, boxShadow: '0 0 40px rgba(0,0,0,0.5)' }}
                onClick={(e) => e.stopPropagation()}
              />
              <div style={{
                position: 'absolute', top: 20, right: 30,
                fontSize: 28, color: '#fff', cursor: 'pointer',
              }} onClick={() => setLightboxImage(null)}>✕</div>
            </div>
          )}

          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={isSaving}
            style={{ width: '100%', marginTop: 8 }}
          >
            {isSaving ? t('editor.saving') : t('editor.save')}
          </button>

          {/* AI生成提示词 */}
          <div style={{ marginTop: 12, borderTop: '1px solid var(--border-color)', paddingTop: 10 }}>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>🤖 {t('editor.ai_condition')}</div>
            <textarea
              className="form-textarea"
              rows={2}
              value={aiHint}
              onChange={(e) => setAiHint(e.target.value)}
              placeholder={t('editor.ai_hint_placeholder')}
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
              {aiGenerating ? `🤖 ${t('editor.generating')}...` : `🤖 ${t('editor.generate_by_condition')}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BlockEditor;
