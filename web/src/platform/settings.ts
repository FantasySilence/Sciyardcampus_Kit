/**
 * 设置缓存（settings.ts）
 *
 * 每个工具的设置由后端持久化为一份 JSON；本模块在内存里缓存这些值，
 * 供设置抽屉和各工具视图读取，避免重复请求。
 */

import { reactive } from 'vue'

import { invoke } from './bridge'

export const settings = reactive<Record<string, Record<string, any>>>({})

// 版本号：后端每次返回新设置后 +1，供需要感知“设置变了”的组件 watch
export const revision = reactive<Record<string, number>>({})

function bump(tool: string) {
  revision[tool] = (revision[tool] ?? 0) + 1
}

export async function loadSettings(tool: string): Promise<Record<string, any>> {
  const data = await invoke<Record<string, any>>('settings_get', tool)
  settings[tool] = data
  bump(tool)
  return data
}

export function getSettings(tool: string): Record<string, any> {
  return settings[tool] ?? {}
}

export async function saveSettings(
  tool: string,
  values: Record<string, any>,
): Promise<Record<string, any>> {
  const saved = await invoke<Record<string, any>>('settings_save', tool, values)
  settings[tool] = saved
  bump(tool)
  return saved
}

export async function resetSettings(tool: string): Promise<Record<string, any>> {
  const data = await invoke<Record<string, any>>('settings_reset', tool)
  settings[tool] = data
  bump(tool)
  return data
}

// 深拷贝（JSON 往返）：复制成可随意编辑的草稿
export function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}
