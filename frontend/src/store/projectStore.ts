import { create } from 'zustand';
import { ProjectData, BlockData, ConnectionData } from '../types/blocks';
import { ProgressData, StoryCard } from '../types/canvas';
import * as api from '../api/blocks';

interface ProjectStore {
  projects: ProjectData[];
  currentProject: ProjectData | null;
  blocks: BlockData[];
  connections: ConnectionData[];
  progress: ProgressData | null;
  storyCards: StoryCard[];
  isLoading: boolean;
  error: string | null;

  // Project actions
  loadProjects: () => Promise<void>;
  loadProject: (id: string) => Promise<void>;
  createProject: (title: string, genre?: string, chapterCount?: number) => Promise<string | null>;
  deleteProject: (id: string) => Promise<void>;

  // Block actions
  loadBlocks: (projectId: string) => Promise<void>;
  addBlock: (projectId: string, data: Partial<BlockData>) => Promise<any>;
  updateBlock: (projectId: string, blockId: string, data: Partial<BlockData>) => Promise<void>;
  removeBlock: (projectId: string, blockId: string) => Promise<void>;

  // Connection actions
  loadConnections: (projectId: string) => Promise<void>;
  addConnection: (projectId: string, data: { from_block: string; to_block: string; conn_type: string; label?: string }) => Promise<any>;
  removeConnection: (projectId: string, connId: string) => Promise<void>;

  // Progress
  loadProgress: (projectId: string) => Promise<void>;

  // Story cards
  loadStoryCards: () => Promise<void>;
  applyStoryCards: (projectId: string, primary: string, secondary: string[]) => Promise<void>;

  setError: (err: string | null) => void;
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  projects: [],
  currentProject: null,
  blocks: [],
  connections: [],
  progress: null,
  storyCards: [],
  isLoading: false,
  error: null,

  setError: (err) => set({ error: err }),

  loadProjects: async () => {
    set({ isLoading: true, error: null });
    try {
      const projects = await api.listProjects();
      set({ projects, isLoading: false });
    } catch (e: any) {
      set({ error: e.message, isLoading: false });
    }
  },

  loadProject: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const project = await api.getProject(id);
      set({
        currentProject: project,
        blocks: project.blocks || [],
        connections: project.connections || [],
        isLoading: false,
      });
    } catch (e: any) {
      set({ error: e.message, isLoading: false });
    }
  },

  createProject: async (title, genre, chapterCount) => {
    set({ isLoading: true, error: null });
    try {
      const result = await api.createProject(title, genre, chapterCount);
      await get().loadProjects();
      set({ isLoading: false });
      return result.id;
    } catch (e: any) {
      set({ error: e.message, isLoading: false });
      return null;
    }
  },

  deleteProject: async (id) => {
    try {
      await api.deleteProject(id);
      await get().loadProjects();
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  loadBlocks: async (projectId) => {
    try {
      const blocks = await api.getBlocks(projectId);
      set({ blocks });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  addBlock: async (projectId, data) => {
    try {
      const result = await api.createBlock(projectId, data);
      await get().loadBlocks(projectId);
      return result;
    } catch (e: any) {
      set({ error: e.message });
      return null;
    }
  },

  updateBlock: async (projectId, blockId, data) => {
    try {
      await api.updateBlock(projectId, blockId, data);
      await get().loadBlocks(projectId);
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  removeBlock: async (projectId, blockId) => {
    try {
      await api.deleteBlock(projectId, blockId);
      await Promise.all([
        get().loadBlocks(projectId),
        get().loadConnections(projectId),
      ]);
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  loadConnections: async (projectId) => {
    try {
      const connections = await api.getConnections(projectId);
      set({ connections });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  addConnection: async (projectId, data) => {
    try {
      const result = await api.createConnection(projectId, data);
      await get().loadConnections(projectId);
      return result;
    } catch (e: any) {
      set({ error: e.message });
      return null;
    }
  },

  removeConnection: async (projectId, connId) => {
    try {
      await api.deleteConnection(projectId, connId);
      await get().loadConnections(projectId);
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  loadProgress: async (projectId) => {
    try {
      const progress = await api.getProgress(projectId);
      set({ progress });
    } catch (e: any) {
      // non-critical
    }
  },

  loadStoryCards: async () => {
    try {
      const cards = await api.getStoryCards();
      set({ storyCards: cards });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  applyStoryCards: async (projectId, primary, secondary) => {
    set({ isLoading: true, error: null });
    try {
      await api.applyStoryCards(projectId, primary, secondary);
      await get().loadProject(projectId);
      set({ isLoading: false });
    } catch (e: any) {
      set({ error: e.message, isLoading: false });
    }
  },
}));
