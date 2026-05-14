export type ViewMode =
  | 'overview'
  | 'character_focus'
  | 'timeline'
  | 'foreshadow_track'
  | 'progress'
  | 'writing'
  | 'screenplay';

export interface StoryCard {
  id: string;
  name: string;
  category: string;
  description: string;
  difficulty: string;
  reference_works: string[];
  compatible_styles: string[];
  auto_blocks: {
    required: Array<{ type: string; canvas: { x: number; y: number }; content_defaults: Record<string, any> }>;
    recommended: Array<{ type: string; canvas: { x: number; y: number }; content_defaults: Record<string, any> }>;
  };
  auto_connections: Array<{ from_type: string; to_type: string; conn_type: string; label: string }>;
  progress_weights: Record<string, number>;
  writing_prompt_modifier: string;
}

export interface ProgressData {
  overall: number;
  categories: Record<string, number>;
  status: string;
  level: number;
}

export interface GenerationEvent {
  stage: string;
  msg: string;
  text?: string;
}

export interface AuditResult {
  passed: boolean;
  has_critical_issues: boolean;
  result: string;
}
