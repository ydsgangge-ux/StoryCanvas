import { create } from 'zustand';
import { LangCode, setLanguage } from '../i18n';

interface UIStore {
  language: LangCode;
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
  showToast: (message: string, type?: 'info' | 'warning' | 'error') => void;
  clearToast: () => void;
  switchLanguage: (lang: LangCode) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  language: 'zh',
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
