/**
 * 主题（theme.ts）
 *
 * 管理深色/浅色主题，并写到 <html data-theme="..."> 上；
 * 具体颜色定义在 styles/tokens.css。
 */

import { ref } from 'vue'

export type Theme = 'dark' | 'light'

export const theme = ref<Theme>('dark')

export function applyTheme(value: Theme): void {
  theme.value = value
  document.documentElement.dataset.theme = value
}

export function toggleTheme(): Theme {
  const next: Theme = theme.value === 'dark' ? 'light' : 'dark'
  applyTheme(next)
  return next
}
