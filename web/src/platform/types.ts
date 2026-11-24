/**
 * 前后端共享的数据结构（只含 TypeScript 类型，编译后不产生运行时代码）
 *
 * 字段名与后端返回的 JSON 一一对应；修改时需同步检查
 * src/scikit/platform/schema.py、session.py、jobs.py 里的定义。
 */

// ------ 设置 schema ------ //
export interface FieldDef {
  key: string
  label: string
  type: 'int' | 'float' | 'bool' | 'enum' | 'string' | 'path'
  default: unknown
  min: number | null
  max: number | null
  step: number | null
  digits: number
  unit: string
  options: { value: string; label: string }[] | null
  hint: string
  // path 字段的选择方式：dir 选目录，file 选文件
  pick: 'dir' | 'file'
}

export interface GroupDef {
  id: string
  label: string
  fields: FieldDef[]
}

export interface SchemaDef {
  version: number
  groups: GroupDef[]
}

export interface ColumnDef {
  key: string
  nameKey: string
  type: 'int' | 'float' | 'string'
  digits?: number
}

export interface ActionDef {
  id: string
  labelKey: string
}

export interface ToolDef {
  id: string
  nameKey: string
  descriptionKey: string
  icon: string
  order: number
  version: string
  actions: ActionDef[]
  columns: ColumnDef[]
  settingsSchema: SchemaDef
}

// ------ 应用状态 ------ //
export interface StorageInfo {
  path: string
  source: string
  portable: boolean
  writable: boolean
  note: string
  resources: string
  version: string
}

export interface AppState {
  version: string
  name: string
  language: string
  theme: 'dark' | 'light'
  lastTool: string
  tools: ToolDef[]
  storage: StorageInfo
  mediaBase: string
}

// ------ 环境自检 ------ //
export interface AdbStatus {
  found: boolean
  path: string
  devices: string[]
  selected?: string
  error?: string
}

export interface TesseractStatus {
  ok: boolean
  path: string
  version: string
  langs: string[]
  missing: string[]
  error: string
  detail?: string
}

export interface EnvStatus {
  data: StorageInfo
  adb: AdbStatus
  tesseract: TesseractStatus
  mouse: { enabled: boolean }
}

// ------ 会话 ------ //
export interface SessionScope {
  mode: 'paper' | 'type'
  paper?: string
  pngType?: string
}

export interface SessionItem {
  index: number
  number: number | null
  kind: string
  png: string
  txt: string
  tags: string[]
  included: boolean
  // Word 里的呈现方式：auto=按标签自动，text=文字，image=原图
  exportMode: 'auto' | 'text' | 'image'
  ocrError: string
  text: string
}

export interface SessionStats {
  total: number
  included: number
  excluded: number
  formula: number
  table: number
  image: number
  // 按当前导出模式统计的“将写文字 / 将贴图”题数
  textCount: number
  imageCount: number
}

export interface Session {
  id: string
  createdAt: string
  updatedAt: string
  source: string
  scope: SessionScope
  items: SessionItem[]
  stats: SessionStats
}

export interface SessionPayload {
  session: Session
  title: string
  docxName: string
  stats: SessionStats
}

export interface HistoryEntry {
  id: string
  title: string
  scope: SessionScope
  source: string
  total: number
  included: number
  updatedAt: string
  docx: string
  docxExists: boolean
}

export interface InventoryItem {
  name: string
  pngs: number
  txts: number
  tags: { formula: number; table: number; image: number }
  docx: string
  updatedAt: string
}

export interface HistoryPayload {
  entries: HistoryEntry[]
  inventory: { types: InventoryItem[]; papers: InventoryItem[] }
}

// ------ 预检 ------ //
export interface ProbeCard {
  headerTop: number
  top: number
  bottom: number
  footer: number
  number: number | null
  kind: string
  complete: boolean
  index: number
}

export interface ProbeResult {
  frame: string
  width: number
  height: number
  cards: ProbeCard[]
  channel: { channel?: string; adb?: string; serial?: string; window?: number[] }
}

// ------ 任务 ------ //
export interface JobLog {
  seq: number
  time: string
  level: 'info' | 'warn' | 'error' | 'success'
  text: string
}

export interface JobProgress {
  current: number
  total: number | null
  label: string
  phase: string
}

export interface JobSnapshot {
  id: string
  kind: string
  title: string
  status: 'running' | 'done' | 'failed' | 'cancelled'
  progress: JobProgress
  logs: JobLog[]
  artifacts: { path: string; meta: Record<string, unknown> }[]
  result: Record<string, any> | null
  error: { code: string; message: string; detail: string } | null
  createdAt: number
  startedAt: number | null
  endedAt: number | null
  elapsed: number
}
