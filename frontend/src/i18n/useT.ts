/**
 * useT — React Hook，自动跟随语言切换重新渲染
 *
 * 用法：
 *   import { useT } from '../i18n/useT';
 *   const { t } = useT();
 *   t('common.save') // → 自动跟随当前语言
 */
import { t, getCurrentLang } from './index';
import { useUIStore } from '../store/uiStore';

export function useT() {
  const lang = useUIStore((s) => s.language);
  // lang 只是用来触发 re-render，实际翻译由模块级 currentPack 提供
  void lang;
  return { t, lang: getCurrentLang() };
}
