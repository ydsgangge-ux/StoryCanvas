import { create } from 'zustand';
import { Node, Edge, Viewport, Connection, addEdge, applyNodeChanges, applyEdgeChanges, NodeChange, EdgeChange } from 'reactflow';
import { BlockData, ConnectionData, BLOCK_COLORS } from '../types/blocks';
import { ViewMode } from '../types/canvas';
import * as api from '../api/blocks';
import { t } from '../i18n';

interface CanvasStore {
  nodes: Node[];
  edges: Edge[];
  allNodes: Node[];       // Unfiltered
  allEdges: Edge[];       // Unfiltered
  viewport: Viewport;
  viewMode: ViewMode;
  focusTarget: string | null;
  selectedBlock: BlockData | null;
  isLoading: boolean;
  /** 记录哪些节点的位置在本地被拖拽修改但尚未保存到后端 */
  dirtyPositions: Record<string, boolean>;

  // Actions
  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  setViewMode: (mode: ViewMode) => void;
  setFocusTarget: (id: string | null) => void;
  setSelectedBlock: (block: BlockData | null) => void;
  setViewport: (viewport: Viewport) => void;
  setLoading: (loading: boolean) => void;

  // Sync from server data
  syncFromBlocks: (blocks: BlockData[], connections: ConnectionData[]) => void;
  /** 保存所有脏位置到后端并清除脏标记 */
  saveDirtyPositions: (projectId: string) => Promise<void>;
  /** 清理指定节点的脏标记 */
  markPositionClean: (nodeId: string) => void;
}

// Block type → ReactFlow node type mapping
// All 33 types mapped; unknown types use 'default' (BaseBlock)
const NODE_TYPE_MAP: Record<string, string> = {
  // Character (7)
  CHARACTER: 'character',
  PERSONALITY: 'default',
  GROWTH: 'default',
  BACKSTORY: 'default',
  CURRENT_STATE: 'default',
  INFORMATION_BOUNDARY: 'default',
  OMNISCIENT_LAYER: 'default',
  // World (5)
  WORLDVIEW: 'default',
  FACTION: 'default',
  RULE_CONSTRAINT: 'default',
  WORLD_DEVELOPMENT: 'default',
  TIMESTAMP: 'default',
  // Structure (9)
  TIMELINE: 'default',
  SCENE: 'scene',
  EVENT: 'default',
  GOAL: 'default',
  CONFLICT: 'default',
  TURNING_POINT: 'default',
  HOOK: 'default',
  FORESHADOW: 'default',
  SURPRISE: 'default',
  // Relationship (2)
  RELATIONSHIP: 'default',
  FACTION_RELATION: 'default',
  // Expression (5)
  ATMOSPHERE: 'default',
  EMOTION_TARGET: 'default',
  RHYTHM: 'default',
  THEME_STATEMENT: 'default',
  LENS: 'default',
  // Screenplay (4)
  SCENE_HEADING: 'default',
  ACTION_LINE: 'default',
  DIALOGUE: 'default',
  VISUAL_MOTIF: 'default',
  // Special (1)
  READER_EMOTION_CURVE: 'default',
  // Story card framework
  STORY_CARD: 'default',
  // Outline blocks
  STORY_OUTLINE: 'default',
  CHAPTER_OUTLINE: 'default',
  CHAPTER_DETAIL: 'default',
  STORY_SYNOPSIS: 'default',
};

// Block types visible in each view mode
const VIEW_MODE_FILTERS: Record<ViewMode, ((block: BlockData) => boolean) | null> = {
  overview: null,       // Show all
  character_focus: (b) => ['CHARACTER', 'PERSONALITY', 'GROWTH', 'BACKSTORY', 'CURRENT_STATE', 'INFORMATION_BOUNDARY', 'RELATIONSHIP'].includes(b.type),
  timeline: (b) => ['TIMELINE', 'SCENE', 'EVENT', 'TIMESTAMP', 'SCENE_HEADING', 'ACTION_LINE', 'DIALOGUE'].includes(b.type),
  foreshadow_track: (b) => ['HOOK', 'FORESHADOW', 'SURPRISE', 'OMNISCIENT_LAYER'].includes(b.type),
  progress: null,      // Show all (progress overlay)
  writing: null,        // Show all
  screenplay: (b) => ['SCENE_HEADING', 'ACTION_LINE', 'DIALOGUE', 'VISUAL_MOTIF', 'CHARACTER'].includes(b.type),
};

export const useCanvasStore = create<CanvasStore>((set, get) => ({
  nodes: [],
  edges: [],
  allNodes: [],
  allEdges: [],
  viewport: { x: 0, y: 0, zoom: 1 },
  viewMode: 'overview',
  focusTarget: null,
  selectedBlock: null,
  isLoading: false,
  dirtyPositions: {},

  setNodes: (nodes) => set({ nodes, allNodes: nodes }),
  setEdges: (edges) => set({ edges, allEdges: edges }),

  onNodesChange: (changes) => {
    const { nodes, dirtyPositions } = get();
    const updated = applyNodeChanges(changes, nodes);

    // 检测拖拽位置变化，标记为脏（用于 syncFromBlocks 保护本地位置不被覆盖）
    const newDirty = { ...dirtyPositions };
    for (const change of changes) {
      if (change.type === 'position' && change.position) {
        newDirty[change.id] = true;
      }
    }

    set({ nodes: updated, allNodes: updated, dirtyPositions: newDirty });
  },

  onEdgesChange: (changes) => {
    const updated = applyEdgeChanges(changes, get().edges);
    set({ edges: updated, allEdges: updated });
  },

  onConnect: (connection) => {
    set({ edges: addEdge({ ...connection, type: 'smoothstep' }, get().edges) });
  },

  setViewMode: (mode) => {
    const { allNodes, allEdges } = get();
    const filter = VIEW_MODE_FILTERS[mode];
    let filteredNodes = allNodes;
    if (filter) {
      filteredNodes = allNodes.filter(n => filter(n.data));
    }
    // Filter edges to only those between visible nodes
    const visibleIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = allEdges.filter(e => visibleIds.has(e.source) && visibleIds.has(e.target));
    set({ viewMode: mode, nodes: filteredNodes, edges: filteredEdges, focusTarget: mode === 'overview' ? null : get().focusTarget });
  },

  setFocusTarget: (id) => set({ focusTarget: id }),
  setSelectedBlock: (block) => set({ selectedBlock: block }),
  setViewport: (viewport) => set({ viewport }),
  setLoading: (loading) => set({ isLoading: loading }),

  saveDirtyPositions: async (projectId) => {
    const { allNodes, dirtyPositions } = get();
    const dirtyIds = Object.keys(dirtyPositions).filter(id => dirtyPositions[id]);
    if (dirtyIds.length === 0) return;

    const moves = dirtyIds.map(id => {
      const node = allNodes.find(n => n.id === id);
      if (!node) return null;
      return { id, canvas_x: node.position.x, canvas_y: node.position.y };
    }).filter(Boolean) as { id: string; canvas_x: number; canvas_y: number }[];

    if (moves.length === 0) return;

    try {
      await api.batchMoveBlocks(projectId, moves);
      set({ dirtyPositions: {} });
    } catch {
      // 保存失败时不清除脏标记，下次会重试
    }
  },

  markPositionClean: (nodeId) => {
    const { dirtyPositions } = get();
    if (dirtyPositions[nodeId]) {
      const updated = { ...dirtyPositions };
      delete updated[nodeId];
      set({ dirtyPositions: updated });
    }
  },

  syncFromBlocks: (blocks, connections) => {
    const { viewMode, dirtyPositions, allNodes: currentNodes } = get();

    // 只显示画布上的块（on_canvas=true），过滤掉块池中的块
    const canvasBlocks = blocks.filter(b => b.on_canvas !== false);

    const nodes: Node[] = canvasBlocks.map((b) => {
      // 如果节点有脏位置（用户拖拽过但未保存），保留本地位置而非后端旧位置
      const existingNode = currentNodes.find(n => n.id === b.id);
      const isDirty = dirtyPositions[b.id];

      return {
        id: b.id,
        type: NODE_TYPE_MAP[b.type] || 'default',
        position: isDirty && existingNode
          ? { ...existingNode.position }
          : { x: b.canvas_x, y: b.canvas_y },
        data: { ...b, label: getBlockTitle(b) },
        style: {
          borderColor: b.color || BLOCK_COLORS[b.type] || '#999',
          width: b.canvas_w,
        },
      };
    });

    const connStyleMap: Record<string, string> = {
      causes: 'default', follows: 'smoothstep', parallels: 'smoothstep',
      foreshadows: 'default', resolves: 'default', contains: 'default',
      conflicts: 'default', influences: 'default',
    };

    const edges: Edge[] = connections.map((c) => ({
      id: c.id,
      source: c.from_block,
      target: c.to_block,
      type: connStyleMap[c.conn_type] || 'smoothstep',
      label: t(`conn.${c.conn_type}`),
      style: { stroke: getConnColor(c.conn_type) },
      animated: c.conn_type === 'foreshadows',
      data: { conn_type: c.conn_type },
    }));

    // Apply current view mode filter
    const filter = VIEW_MODE_FILTERS[viewMode];
    let filteredNodes = nodes;
    if (filter) {
      filteredNodes = nodes.filter(n => filter(n.data));
    }
    const visibleIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = edges.filter(e => visibleIds.has(e.source) && visibleIds.has(e.target));

    set({ nodes: filteredNodes, edges: filteredEdges, allNodes: nodes, allEdges: edges });
  },
}));

function getBlockTitle(block: BlockData): string {
  const content = block.content || {};
  if (block.type === 'CHARACTER') return content.name || t('char.new_character');
  if (block.type === 'SCENE') return content.title || t('block.new_scene');
  if (block.type === 'TIMELINE') return content.timeline_name || t('block.new_timeline');
  if (block.type === 'EVENT') return content.title || t('block.new_event');
  if (block.type === 'HOOK') return content.title || t('block.new_hook');
  if (block.type === 'WORLDVIEW') return content.world_name || t('block.new_worldview');
  if (block.type === 'FACTION') return content.name || t('block.new_faction');
  if (block.type === 'GOAL') return content.surface_goal || t('block.new_goal');
  if (block.type === 'CONFLICT') return content.title || t('block.new_conflict');
  if (block.type === 'TURNING_POINT') return content.title || t('block.new_turning');
  if (block.type === 'RELATIONSHIP') return `${content.relationship_type || t('block.relationship')}`;
  if (block.type === 'STORY_CARD') return content.card_name || content.card_id || t('block.story_card');
  if (block.type === 'STORY_OUTLINE') return content.title || t('block.story_outline');
  if (block.type === 'CHAPTER_OUTLINE') return `${t('field.chapter')}${content.chapter_number || '?'} ${content.title || t('block.outline')}`;
  if (block.type === 'CHAPTER_DETAIL') return `${t('field.chapter')}${content.chapter_number || '?'}${t('block.detail')}: ${content.title || ''}`;
  if (block.type === 'STORY_SYNOPSIS') return content.title || t('block.story_synopsis');
  return t(`block.${block.type}`);
}

function getConnColor(type: string): string {
  const colors: Record<string, string> = {
    causes: '#666', follows: '#999', parallels: '#4A90D9',
    foreshadows: '#F39C12', resolves: '#50C878', contains: '#333',
    conflicts: '#E74C3C', influences: '#9370DB',
  };
  return colors[type] || '#999';
}
