import { create } from 'zustand';
import { LangCode, setLanguage } from '../i18n';

const AI_FILL_HINTS_KEY = 'sc_ai_fill_hints';

function loadAiFillHints(): Record<string, string> {
  try {
    const raw = localStorage.getItem(AI_FILL_HINTS_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

interface UIStore {
  language: LangCode;
  /** 每个块的 AI 生成提示词草稿，按 blockId 暂存（localStorage 持久化） */
  aiFillHints: Record<string, string>;
  showStoryCardPicker: boolean;
  showBlockEditor: boolean;
  showWritingPanel: boolean;
  showProjectList: boolean;
  showTrackingPanel: boolean;
  showBlockPool: boolean;
  showLLMSettings: boolean;
  activeTab: 'canvas' | 'writing';
  toastMessage: string | null;
  toastType: 'info' | 'warning' | 'error';

  setShowStoryCardPicker: (show: boolean) => void;
  setShowBlockEditor: (show: boolean) => void;
  setShowWritingPanel: (show: boolean) => void;
  setShowProjectList: (show: boolean) => void;
  setShowTrackingPanel: (show: boolean) => void;
  setShowBlockPool: (show: boolean) => void;
  setShowLLMSettings: (show: boolean) => void;
  setActiveTab: (tab: 'canvas' | 'writing') => void;
  setAiFillHint: (blockId: string, hint: string) => void;
  showToast: (message: string, type?: 'info' | 'warning' | 'error') => void;
  clearToast: () => void;
  switchLanguage: (lang: LangCode) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  language: 'zh',
  aiFillHints: loadAiFillHints(),
  showStoryCardPicker: false,
  showBlockEditor: false,
  showWritingPanel: false,
  showProjectList: false,
  showTrackingPanel: false,
  showBlockPool: false,
  showLLMSettings: false,
  activeTab: 'canvas',
  toastMessage: null,
  toastType: 'info',

  setShowStoryCardPicker: (show) => set({ showStoryCardPicker: show }),
  setShowBlockEditor: (show) => set({ showBlockEditor: show }),
  setShowWritingPanel: (show) => set({ showWritingPanel: show }),
  setShowProjectList: (show) => set({ showProjectList: show }),
  setShowTrackingPanel: (show) => set({ showTrackingPanel: show }),
  setShowBlockPool: (show) => set({ showBlockPool: show }),
  setShowLLMSettings: (show) => set({ showLLMSettings: show }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setAiFillHint: (blockId, hint) => set((state) => {
    const next = { ...state.aiFillHints };
    if (hint) {
      next[blockId] = hint;
    } else {
      delete next[blockId];
    }
    try {
      localStorage.setItem(AI_FILL_HINTS_KEY, JSON.stringify(next));
    } catch {
      // 忽略隐私模式/配额不足等写入失败
    }
    return { aiFillHints: next };
  }),
  showToast: (message, type = 'info') => {
    set({ toastMessage: message, toastType: type });
    setTimeout(() => set({ toastMessage: null }), 3000);
  },
  clearToast: () => set({ toastMessage: null }),
  switchLanguage: (lang) => {
    setLanguage(lang);
    set({ language: lang });
  },
}));
