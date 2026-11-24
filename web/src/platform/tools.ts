/**
 * 工具视图注册表（tools.ts）
 *
 * 用 Vite 的 import.meta.glob 在构建时收集 web/src/tools/<id>/View.vue，
 * 得到“路径 → 懒加载函数”的映射；运行时按工具 id 取对应视图。
 * 工具 id 必须与目录名一致。
 */

const views = import.meta.glob('../tools/*/View.vue') as Record<
  string,
  () => Promise<{ default: unknown }>
>

export function viewFor(id: string): (() => Promise<{ default: unknown }>) | null {
  return views[`../tools/${id}/View.vue`] ?? null
}

export function hasView(id: string): boolean {
  return Boolean(viewFor(id))
}
