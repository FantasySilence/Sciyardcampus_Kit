/**
 * 媒体地址（media.ts）
 *
 * 后端用本地 HTTP 托管 <data>/resources 下的图片，并支持 ?w= 生成缩略图。
 * 开发模式前端跑在 Vite 端口，必须拼后端给的绝对地址；
 * 生产模式也统一用 app_state.mediaBase，避免相对路径歧义。
 */

import { ref } from 'vue'

// 后端 mediaBase，形如 http://127.0.0.1:12345；由 App.vue 在启动时写入
export const mediaBase = ref('')

export function setMediaBase(value: string): void {
  mediaBase.value = (value || '').replace(/\/$/, '')
}

/**
 * 生成图片地址。
 * path 是数据根下的相对路径（如 resources/row_pngs/选择题/21.png）；
 * width 大于 0 时走后端缩略图缓存。
 */
export function mediaUrl(path: string, width = 0): string {
  if (!path) return ''
  const params = new URLSearchParams({ path })
  if (width > 0) params.set('w', String(width))
  return `${mediaBase.value}/media?${params.toString()}`
}
