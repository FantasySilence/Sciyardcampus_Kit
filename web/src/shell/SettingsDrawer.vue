<!--
  SettingsDrawer.vue —— 设置抽屉（schema 驱动）

  三个标签页：
  - 工具参数：按当前工具 settingsSchema 的 groups/fields 动态渲染；
  - 数据与存储：显示/切换数据目录；
  - 关于：版本与说明。

  字段类型 int/float 渲染数字输入框，bool 勾选，enum 下拉，
  string 文本框，path 文本框 + 选择按钮（按 field.pick 决定选文件还是目录）。
  抽屉不写死任何字段，新增设置项只改后端 schema.py。
-->
<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { invoke } from '../platform/bridge'
import { t } from '../platform/i18n'
import { clone, loadSettings, resetSettings, saveSettings, settings } from '../platform/settings'
import { notify, notifyError } from '../platform/toast'
import type { CacheInfo, FieldDef, StorageInfo, ToolDef } from '../platform/types'

const props = defineProps<{ tool: ToolDef }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'saved'): void }>()

const tab = ref<'tool' | 'storage' | 'about'>('tool')
const draft = reactive<Record<string, any>>({})
const saving = ref(false)
const resetArmed = ref(false)
const storage = ref<StorageInfo | null>(null)
const cache = ref<CacheInfo | null>(null)
const cacheArmed = ref(false)

// ------ 草稿读写 ------ //
function syncDraft(source: Record<string, any>) {
  Object.keys(draft).forEach((key) => delete draft[key])
  Object.assign(draft, clone(source))
}

function read(path: string): any {
  return path.split('.').reduce<any>((node, key) => (node == null ? undefined : node[key]), draft)
}

function write(path: string, value: unknown) {
  const parts = path.split('.')
  let node: any = draft
  for (const part of parts.slice(0, -1)) {
    if (typeof node[part] !== 'object' || node[part] === null) node[part] = {}
    node = node[part]
  }
  node[parts[parts.length - 1]] = value
}

// ------ 表单事件 ------ //
function onNumber(field: FieldDef, event: Event) {
  const raw = (event.target as HTMLInputElement).value
  write(field.key, raw === '' ? null : Number(raw))
}

function onBool(field: FieldDef, event: Event) {
  write(field.key, (event.target as HTMLInputElement).checked)
}

function onEnum(field: FieldDef, event: Event) {
  write(field.key, (event.target as HTMLSelectElement).value)
}

function onText(field: FieldDef, event: Event) {
  write(field.key, (event.target as HTMLInputElement).value)
}

async function pickPath(field: FieldDef) {
  try {
    const result = await invoke<{ cancelled?: boolean; path?: string }>(
      'file_pick',
      field.pick === 'file' ? 'file' : 'dir',
    )
    if (!result || result.cancelled || !result.path) return
    write(field.key, result.path)
  } catch (error) {
    notifyError(error)
  }
}

const stepFor = (field: FieldDef) =>
  field.step ?? (field.type === 'int' ? 1 : Math.pow(10, -Math.min(field.digits, 6)))

// ------ 保存 / 重置 ------ //
async function save() {
  saving.value = true
  try {
    const saved = await saveSettings(props.tool.id, clone(draft))
    syncDraft(saved)
    notify('success', t('settings.saved'))
    emit('saved')
  } catch (error) {
    notifyError(error)
  } finally {
    saving.value = false
  }
}

async function reset() {
  if (!resetArmed.value) {
    resetArmed.value = true
    window.setTimeout(() => (resetArmed.value = false), 3000)
    return
  }
  resetArmed.value = false
  try {
    const data = await resetSettings(props.tool.id)
    syncDraft(data)
    notify('success', t('settings.resetDone'))
    emit('saved')
  } catch (error) {
    notifyError(error)
  }
}

// ------ 数据目录 ------ //
async function refreshStorage() {
  try {
    storage.value = await invoke<StorageInfo>('storage_info')
  } catch (error) {
    notifyError(error)
  }
}

async function changeDir() {
  try {
    const result = await invoke<{ cancelled?: boolean; path?: string }>('storage_pick_dir')
    if (!result || result.cancelled || !result.path) return
    storage.value = await invoke<StorageInfo>('storage_set_dir', result.path)
    await loadSettings(props.tool.id)
    syncDraft(settings[props.tool.id] ?? {})
    notify('success', t('storage.changed'))
    emit('saved')
  } catch (error) {
    notifyError(error)
  }
}

async function resetDir() {
  try {
    storage.value = await invoke<StorageInfo>('storage_reset')
    await loadSettings(props.tool.id)
    syncDraft(settings[props.tool.id] ?? {})
    notify('success', t('storage.changed'))
    emit('saved')
  } catch (error) {
    notifyError(error)
  }
}

async function openDir() {
  try {
    await invoke('storage_open_dir')
  } catch (error) {
    notifyError(error)
  }
}

// ------ 缓存 ------ //
function formatSize(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value >= 10 || index === 0 ? Math.round(value) : value.toFixed(1)} ${units[index]}`
}

async function refreshCache() {
  try {
    cache.value = await invoke<CacheInfo>('storage_cache_info')
  } catch (error) {
    notifyError(error)
  }
}

async function clearCache() {
  if (!cacheArmed.value) {
    cacheArmed.value = true
    window.setTimeout(() => (cacheArmed.value = false), 3000)
    return
  }
  cacheArmed.value = false
  try {
    const result = await invoke<{
      freedBytes: number
      removed: number
      skipped: number
      cache: CacheInfo
    }>('storage_clear_cache')
    cache.value = result.cache
    notify(
      'success',
      t('storage.cacheCleared', { size: formatSize(result.freedBytes) }),
      result.skipped ? t('storage.cacheSkipped', { n: result.skipped }) : '',
    )
  } catch (error) {
    notifyError(error)
  }
}

const sourceLabel = computed(() => {
  const source = storage.value?.source ?? 'default'
  return t(`storage.source.${source}`)
})

// ------ 生命周期 ------ //
onMounted(async () => {
  if (!settings[props.tool.id]) {
    try {
      await loadSettings(props.tool.id)
    } catch (error) {
      notifyError(error)
    }
  }
  syncDraft(settings[props.tool.id] ?? {})
  await refreshStorage()
  await refreshCache()
})

watch(
  () => props.tool.id,
  async (id) => {
    if (!settings[id]) await loadSettings(id)
    syncDraft(settings[id] ?? {})
  },
)
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <aside class="drawer">
      <header class="drawer-head">
        <div>
          <div class="drawer-title">{{ t('settings.title') }}</div>
          <div class="muted">{{ t(tool.nameKey) }}</div>
        </div>
        <button class="btn ghost" @click="emit('close')">✕</button>
      </header>

      <div class="tabs">
        <button class="tab" :class="{ active: tab === 'tool' }" @click="tab = 'tool'">
          {{ t('settings.tool') }}
        </button>
        <button class="tab" :class="{ active: tab === 'storage' }" @click="tab = 'storage'">
          {{ t('settings.storage') }}
        </button>
        <button class="tab" :class="{ active: tab === 'about' }" @click="tab = 'about'">
          {{ t('settings.about') }}
        </button>
      </div>

      <div class="drawer-body">
        <template v-if="tab === 'tool'">
          <!-- 空 schema（作业发布占位）时给出说明 -->
          <div v-if="!tool.settingsSchema.groups.length" class="empty">
            {{ t('settings.noFields') }}
          </div>

          <section v-for="group in tool.settingsSchema.groups" :key="group.id" class="group">
            <div class="group-title">{{ t(group.label) }}</div>
            <div v-for="field in group.fields" :key="field.key" class="field">
              <label class="field-label">
                <span>{{ t(field.label) }}</span>
                <span v-if="field.unit" class="unit">
                  {{ field.unit.includes('.') ? t(field.unit) : field.unit }}
                </span>
              </label>

              <select
                v-if="field.type === 'enum'"
                class="input"
                :value="read(field.key)"
                @change="onEnum(field, $event)"
              >
                <option
                  v-for="option in field.options ?? []"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ t(option.label) }}
                </option>
              </select>

              <label v-else-if="field.type === 'bool'" class="switch">
                <input
                  type="checkbox"
                  :checked="Boolean(read(field.key))"
                  @change="onBool(field, $event)"
                />
                <span>{{ t('settings.enabled') }}</span>
              </label>

              <div v-else-if="field.type === 'string' || field.type === 'path'" class="path-field">
                <input
                  class="input mono"
                  type="text"
                  :value="read(field.key)"
                  @input="onText(field, $event)"
                />
                <button v-if="field.type === 'path'" class="btn sm" @click="pickPath(field)">
                  {{ field.pick === 'file' ? t('settings.pickFile') : t('settings.pickDir') }}
                </button>
              </div>

              <input
                v-else
                class="input mono"
                type="number"
                :value="read(field.key)"
                :step="stepFor(field)"
                @input="onNumber(field, $event)"
              />

              <div v-if="field.hint" class="hint">{{ t(field.hint) }}</div>
            </div>
          </section>

          <div v-if="tool.settingsSchema.groups.length" class="drawer-actions">
            <button class="btn primary" :disabled="saving" @click="save">
              {{ t('action.save') }}
            </button>
            <button class="btn" @click="reset">
              {{ resetArmed ? t('settings.confirmReset') : t('action.reset') }}
            </button>
          </div>
        </template>

        <template v-else-if="tab === 'storage'">
          <div class="field">
            <div class="field-label">
              <span>{{ t('storage.current') }}</span>
              <span class="badge">{{ sourceLabel }}</span>
            </div>
            <div class="path mono">{{ storage?.path }}</div>
            <div v-if="storage?.note" class="hint warn">{{ storage.note }}</div>
          </div>

          <div class="hint">{{ t('storage.hint') }}</div>

          <div class="storage-grid">
            <button class="btn" @click="changeDir">{{ t('storage.change') }}</button>
            <button class="btn" @click="openDir">{{ t('storage.open') }}</button>
            <button class="btn" @click="resetDir">{{ t('storage.reset') }}</button>
          </div>

          <div class="cache">
            <div class="field-label">
              <span>{{ t('storage.cacheTitle') }}</span>
              <span class="badge">
                {{ t('storage.cacheSize', { size: formatSize(cache?.bytes ?? 0), n: cache?.files ?? 0 }) }}
              </span>
            </div>
            <div class="hint">{{ t('storage.cacheHint') }}</div>
            <div class="storage-grid">
              <button class="btn" :disabled="!cache?.files" @click="clearCache">
                {{ cacheArmed ? t('storage.cacheConfirm') : t('storage.clearCache') }}
              </button>
              <button class="btn" @click="refreshCache">{{ t('action.refresh') }}</button>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="about">
            <div class="about-title">{{ t('app.name') }}</div>
            <div class="muted">v{{ storage?.version }}</div>
            <p class="hint">{{ t('about.intro') }}</p>
            <p class="hint">{{ t('about.license') }}</p>
          </div>
        </template>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: var(--scrim);
  display: flex;
  justify-content: flex-end;
  z-index: 60;
  backdrop-filter: blur(2px);
}

.drawer {
  width: 520px;
  max-width: 92vw;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border-left: 1px solid var(--line);
  box-shadow: var(--shadow);
}

.drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 18px 10px;
}

.drawer-title {
  font-size: 15px;
  font-weight: 600;
}

.drawer .tabs {
  margin: 0 18px;
}

.drawer-body {
  flex: 1;
  overflow: auto;
  padding: 16px 18px 24px;
}

.group {
  margin-bottom: 18px;
}

.group-title {
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--line);
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.switch {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
}

.path-field {
  display: flex;
  gap: 8px;
}

.path-field .input {
  flex: 1;
  min-width: 0;
}

.drawer-actions {
  display: flex;
  gap: 8px;
  margin-top: 20px;
}

.path {
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--bg);
  border: 1px solid var(--line);
  font-size: 11px;
  word-break: break-all;
}

.storage-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin: 14px 0;
}

.cache {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}

.about-title {
  font-size: 18px;
  color: var(--brand);
}
</style>
