// StoryCanvas 块类型定义

export type BlockType =
  | 'CHARACTER' | 'PERSONALITY' | 'GROWTH' | 'BACKSTORY' | 'CURRENT_STATE'
  | 'INFORMATION_BOUNDARY' | 'OMNISCIENT_LAYER'
  | 'WORLDVIEW' | 'FACTION' | 'RULE_CONSTRAINT' | 'WORLD_DEVELOPMENT' | 'TIMESTAMP'
  | 'TIMELINE' | 'SCENE' | 'EVENT' | 'GOAL' | 'CONFLICT' | 'TURNING_POINT'
  | 'HOOK' | 'FORESHADOW' | 'SURPRISE'
  | 'RELATIONSHIP' | 'FACTION_RELATION'
  | 'ATMOSPHERE' | 'EMOTION_TARGET' | 'RHYTHM' | 'THEME_STATEMENT' | 'LENS'
  | 'SCENE_HEADING' | 'ACTION_LINE' | 'DIALOGUE' | 'VISUAL_MOTIF'
  | 'READER_EMOTION_CURVE'
  | 'STORY_CARD' | 'STORY_OUTLINE' | 'CHAPTER_OUTLINE' | 'CHAPTER_DETAIL' | 'STORY_SYNOPSIS'
  | 'STORYBOARD';

export type ConnType =
  | 'causes' | 'follows' | 'parallels' | 'foreshadows'
  | 'resolves' | 'contains' | 'conflicts' | 'influences';

export interface BlockCanvas {
  x: number;
  y: number;
  width: number;
  collapsed: boolean;
  color: string | null;
  timeline_anchor: string;
}

export interface BlockMeta {
  completeness: number;
  tags: string[];
  notes: string;
}

export interface BlockConnection {
  to: string;
  type: ConnType;
  label: string;
  chapter_hint: string;
}

export interface BlockData {
  id: string;
  type: BlockType;
  project_id: string;
  canvas_x: number;
  canvas_y: number;
  canvas_w: number;
  collapsed: boolean;
  color: string | null;
  timeline_id: string | null;
  chapter_pos: string | null;
  completeness: number;
  tags: string[];
  notes: string;
  content: Record<string, any>;
  is_draft: boolean;
  on_canvas: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConnectionData {
  id: string;
  project_id: string;
  from_block: string;
  to_block: string;
  conn_type: ConnType;
  label: string | null;
  chapter_hint: string | null;
  created_at: string;
}

export interface ProjectData {
  id: string;
  title: string;
  genre: string | null;
  story_cards: string;
  style_sig: string;
  omniscient: string;
  chapter_count: number;
  experience_flags: string;
  created_at: string;
  updated_at: string;
}

// Block Chinese labels
export const BLOCK_LABELS: Record<string, string> = {
  CHARACTER: '角色',
  PERSONALITY: '性格',
  GROWTH: '成长',
  BACKSTORY: '过去',
  CURRENT_STATE: '当前状态',
  INFORMATION_BOUNDARY: '信息边界',
  OMNISCIENT_LAYER: '全知层',
  WORLDVIEW: '世界观',
  FACTION: '势力',
  RULE_CONSTRAINT: '规则约束',
  WORLD_DEVELOPMENT: '世界发展',
  TIMESTAMP: '时间戳',
  TIMELINE: '时间线',
  SCENE: '场景',
  EVENT: '事件',
  GOAL: '目标',
  CONFLICT: '冲突',
  TURNING_POINT: '转折点',
  HOOK: '悬念',
  FORESHADOW: '铺垫',
  SURPRISE: '意外',
  RELATIONSHIP: '角色关系',
  FACTION_RELATION: '势力关系',
  ATMOSPHERE: '意境',
  EMOTION_TARGET: '情绪目标',
  RHYTHM: '节奏',
  THEME_STATEMENT: '主题',
  LENS: '镜头',
  SCENE_HEADING: '场景头',
  ACTION_LINE: '动作行',
  DIALOGUE: '对白',
  VISUAL_MOTIF: '视觉主题',
  READER_EMOTION_CURVE: '读者情绪曲线',
  STORY_CARD: '故事卡框架',
  STORY_OUTLINE: '故事大纲',
  CHAPTER_OUTLINE: '章节大纲',
  CHAPTER_DETAIL: '章节细纲',
  STORY_SYNOPSIS: '故事简介',
  STORYBOARD: '分镜头脚本',
};

// Connection type Chinese labels
export const CONN_LABELS: Record<string, string> = {
  causes: '因果',
  follows: '时序',
  parallels: '并行',
  foreshadows: '铺垫',
  resolves: '回收',
  contains: '包含',
  conflicts: '冲突',
  influences: '影响',
};

// Block color map
export const BLOCK_COLORS: Record<string, string> = {
  CHARACTER: '#4A90D9',
  PERSONALITY: '#6BA3D6',
  GROWTH: '#5B9BD5',
  BACKSTORY: '#4472C4',
  CURRENT_STATE: '#70B0D8',
  INFORMATION_BOUNDARY: '#2E75B6',
  OMNISCIENT_LAYER: '#FFD700',
  WORLDVIEW: '#7B68EE',
  FACTION: '#9370DB',
  RULE_CONSTRAINT: '#8A2BE2',
  WORLD_DEVELOPMENT: '#A78BFA',
  TIMESTAMP: '#C4B5FD',
  TIMELINE: '#4A90D9',
  SCENE: '#50C878',
  EVENT: '#3CB371',
  GOAL: '#90EE90',
  CONFLICT: '#E74C3C',
  TURNING_POINT: '#FF6B6B',
  HOOK: '#E8873A',
  FORESHADOW: '#F39C12',
  SURPRISE: '#FF8C00',
  RELATIONSHIP: '#FF69B4',
  FACTION_RELATION: '#DB7093',
  ATMOSPHERE: '#708090',
  EMOTION_TARGET: '#778899',
  RHYTHM: '#808080',
  THEME_STATEMENT: '#696969',
  LENS: '#2F4F4F',
  SCENE_HEADING: '#1C1C1C',
  ACTION_LINE: '#333333',
  DIALOGUE: '#555555',
  VISUAL_MOTIF: '#404040',
  READER_EMOTION_CURVE: '#FFA500',
  STORY_CARD: '#FFD700',
  STORY_OUTLINE: '#C0C0C0',
  CHAPTER_OUTLINE: '#A9A9A9',
  CHAPTER_DETAIL: '#808080',
  STORY_SYNOPSIS: '#B0C4DE',
  STORYBOARD: '#FF6347',
};

// Block type category for progress bar
export const BLOCK_CATEGORIES: Record<string, string> = {
  CHARACTER: 'character', PERSONALITY: 'character', GROWTH: 'character',
  BACKSTORY: 'character', CURRENT_STATE: 'character', INFORMATION_BOUNDARY: 'character',
  OMNISCIENT_LAYER: 'world',
  WORLDVIEW: 'world', FACTION: 'world', RULE_CONSTRAINT: 'world',
  WORLD_DEVELOPMENT: 'world', TIMESTAMP: 'world',
  TIMELINE: 'structure', SCENE: 'structure', EVENT: 'structure', GOAL: 'structure',
  CONFLICT: 'structure', TURNING_POINT: 'structure', HOOK: 'structure',
  FORESHADOW: 'structure', SURPRISE: 'structure',
  RELATIONSHIP: 'tension', FACTION_RELATION: 'tension',
  READER_EMOTION_CURVE: 'tension', EMOTION_TARGET: 'tension', RHYTHM: 'tension',
  STORY_CARD: 'structure',
  STORY_OUTLINE: 'structure',
  CHAPTER_OUTLINE: 'structure',
  CHAPTER_DETAIL: 'structure',
  STORY_SYNOPSIS: 'structure',
  STORYBOARD: 'structure',
};

export const CATEGORY_LABELS: Record<string, string> = {
  world: '世界层', character: '角色层', structure: '结构层', tension: '张力层',
};

export const CONNECTION_STYLE: Record<string, { stroke: string; strokeDasharray?: string; markerEnd?: string }> = {
  causes: { stroke: '#666', markerEnd: 'arrow' },
  follows: { stroke: '#999', strokeDasharray: '5,5' },
  parallels: { stroke: '#4A90D9', strokeDasharray: '10,5' },
  foreshadows: { stroke: '#F39C12', strokeDasharray: '3,3' },
  resolves: { stroke: '#50C878' },
  contains: { stroke: '#333' },
  conflicts: { stroke: '#E74C3C' },
  influences: { stroke: '#9370DB', strokeDasharray: '5,5' },
};
