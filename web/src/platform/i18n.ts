/**
 * 多语言（i18n）
 *
 * 负责把外壳与各工具的 JSON 词典按语言合并成内存表，并提供 t() 取文案。
 * 词典来源（构建时由 Vite 的 import.meta.glob 收集）：
 * - web/src/i18n/*.json：外壳文案；
 * - web/src/tools/<id>/i18n/*.json：各工具自己的文案。
 */

import { computed, ref } from 'vue'

type Dict = Record<string, string>

const shellModules = import.meta.glob('../i18n/*.json', { eager: true }) as Record<string, any>
const toolModules = import.meta.glob('../tools/*/i18n/*.json', { eager: true }) as Record<string, any>

const messages: Record<string, Dict> = {}

function merge(lang: string, dict: Dict) {
  messages[lang] = { ...(messages[lang] ?? {}), ...dict }
}

for (const [path, mod] of Object.entries(shellModules)) {
  const lang = path.split('/').pop()?.replace('.json', '') ?? 'zh_CN'
  merge(lang, (mod.default ?? mod) as Dict)
}
for (const [path, mod] of Object.entries(toolModules)) {
  const lang = path.split('/').pop()?.replace('.json', '') ?? 'zh_CN'
  merge(lang, (mod.default ?? mod) as Dict)
}

export const locale = ref('zh_CN')
export const languages = computed(() => Object.keys(messages).sort())

/**
 * 取文案：当前语言 → 简体中文 → key 本身。
 * params 用于占位符替换，如 t('x', { n: 3 })。
 */
export function t(key: string, params?: Record<string, string | number>): string {
  const dict = messages[locale.value] ?? {}
  let text = dict[key] ?? messages.zh_CN?.[key] ?? key
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      text = text.replaceAll(`{${name}}`, String(value))
    }
  }
  return text
}

export function setLocale(lang: string): void {
  if (!messages[lang]) return
  locale.value = lang
  document.documentElement.lang = lang.replace('_', '-')
}
