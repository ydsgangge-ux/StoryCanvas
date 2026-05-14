/**
 * StoryCanvas i18n — 国际化
 * 纯函数模块，无 React 依赖，可在任何地方使用。
 */

import zh from './zh';
import en from './en';

export type LangCode = 'zh' | 'en';

const PACKS: Record<LangCode, Record<string, string>> = { zh, en };

let currentLang: LangCode = 'zh';
let currentPack = zh;

export function t(key: string, params?: Record<string, string | number>): string {
  let text = currentPack[key];
  if (text === undefined) text = zh[key];
  if (text === undefined) return key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      text = text.replace(`{${k}}`, String(v));
    }
  }
  return text;
}

export function setLanguage(lang: LangCode): void {
  currentLang = lang;
  currentPack = PACKS[lang] || zh;
}

export function getCurrentLang(): LangCode {
  return currentLang;
}
