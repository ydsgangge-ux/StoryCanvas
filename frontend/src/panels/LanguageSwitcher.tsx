import React from 'react';
import { useUIStore } from '../store/uiStore';

const LanguageSwitcher: React.FC = () => {
  const lang = useUIStore((s) => s.language);
  const switchLanguage = useUIStore((s) => s.switchLanguage);

  return (
    <button
      className="btn btn-sm btn-ghost"
      style={{ fontSize: 11, padding: '2px 6px' }}
      onClick={() => switchLanguage(lang === 'zh' ? 'en' : 'zh')}
      title={lang === 'zh' ? 'Switch to English' : '切换到中文'}
    >
      {lang === 'zh' ? 'EN' : '中'}
    </button>
  );
};

export default LanguageSwitcher;
