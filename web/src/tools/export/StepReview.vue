<!--
  StepReview.vue —— 第②步：预览检查

  负责：
  - 逐题展示「截图 + OCR 文字 + 标签」；
  - 剔除/恢复题目（写回 session，导出时跳过）；
  - 单题重新识别（调 start_ocr，完成后刷新会话）；
  - 统计与分页；确认后 emit('export')。
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { callTool, invoke } from '../../platform/bridge'
import { t } from '../../platform/i18n'
import { useJob } from '../../platform/jobs'
import { mediaUrl } from '../../platform/media'
import { notify, notifyError } from '../../platform/toast'
import type { SessionItem, SessionPayload } from '../../platform/types'
import LogConsole from '../../ui/LogConsole.vue'
import ProgressBar from '../../ui/ProgressBar.vue'

const props = defineProps<{ payload: SessionPayload }>()
const emit = defineEmits<{
  (e: 'updated', payload: SessionPayload): void
  (e: 'export'): void
  (e: 'back'): void
  (e: 'reset'): void
}>()

const filter = ref<'all' | 'check' | 'excluded'>('all')
const page = ref(1)
const pageSize = 24
const selectedIndex = ref<number | null>(null)
const busy = ref(false)
const job = useJob()
const handled = ref('')

// 纯文字编辑：草稿 + 自动保存状态（700ms 防抖，切题/离开前强制保存）
const draftText = ref('')
const draftIndex = ref<number | null>(null)
const saveState = ref<'saved' | 'unsaved' | 'saving' | 'error'>('saved')
let saveTimer = 0
let saveVersion = 0
const dirty = ref(false)

const sessionId = computed(() => props.payload.session.id)
const items = computed(() => props.payload.session.items)
const stats = computed(() => props.payload.stats)

const filtered = computed(() => {
  if (filter.value === 'check') {
    return items.value.filter((item) => item.tags.length > 0 || item.ocrError)
  }
  if (filter.value === 'excluded') {
    return items.value.filter((item) => !item.included)
  }
  return items.value
})

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize)))
const paged = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})

const selected = computed<SessionItem | null>(() => {
  if (selectedIndex.value === null) return paged.value[0] ?? filtered.value[0] ?? null
  return items.value.find((item) => item.index === selectedIndex.value) ?? null
})

watch(filter, () => {
  page.value = 1
  selectedIndex.value = null
})

const saveStateLabel = computed(() => t(`export.review.saveState.${saveState.value}`))

function tagLabel(tag: string): string {
  return t(`export.tag.${tag}`)
}

function modeLabel(mode: string): string {
  return t(`export.review.mode.${mode}`)
}

/** 这道题实际会以文字还是图片进入 Word（auto 时按标签判断）。 */
function effectiveMode(item: SessionItem | null): 'text' | 'image' {
  if (!item) return 'text'
  if (item.exportMode === 'text' || item.exportMode === 'image') return item.exportMode
  return item.tags.length ? 'image' : 'text'
}

function selectItem(item: SessionItem) {
  selectedIndex.value = item.index
}

/** 把当前草稿写回 txt；返回时保证草稿已落盘。 */
async function flushSave(): Promise<void> {
  window.clearTimeout(saveTimer)
  saveTimer = 0
  if (!dirty.value || draftIndex.value === null) return

  const index = draftIndex.value
  const text = draftText.value
  const version = ++saveVersion
  dirty.value = false
  saveState.value = 'saving'
  try {
    const data = await callTool<SessionPayload>('export', 'save_text', {
      sessionId: sessionId.value,
      index,
      text,
    })
    emit('updated', data)
    if (version === saveVersion && !dirty.value) saveState.value = 'saved'
  } catch (error) {
    dirty.value = true
    saveState.value = 'error'
    notifyError(error)
  }
}

function onTextInput() {
  dirty.value = true
  saveState.value = 'unsaved'
  window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => {
    void flushSave()
  }, 700)
}

async function setMode(mode: string) {
  if (!selected.value) return
  if (mode !== 'auto' && mode !== 'text' && mode !== 'image') return
  await flushSave()
  try {
    const data = await callTool<SessionPayload>('export', 'set_render_mode', {
      sessionId: sessionId.value,
      index: selected.value.index,
      mode,
    })
    emit('updated', data)
    notify('success', t('export.review.modeChanged'))
  } catch (error) {
    notifyError(error)
  }
}

async function goExport() {
  await flushSave()
  emit('export')
}

async function goBack() {
  await flushSave()
  emit('back')
}

watch(
  () => selected.value?.index,
  async (index) => {
    if (index === null || index === undefined) return
    if (draftIndex.value === index) return
    if (dirty.value) await flushSave()
    draftIndex.value = index
    draftText.value = selected.value?.text ?? ''
    dirty.value = false
    saveState.value = 'saved'
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  window.clearTimeout(saveTimer)
  if (dirty.value) void flushSave()
})

async function refresh() {
  if (!sessionId.value) return
  const data = await callTool<SessionPayload>('export', 'session_get', {
    sessionId: sessionId.value,
  })
  emit('updated', data)
}

async function toggle(item: SessionItem) {
  if (busy.value) return
  busy.value = true
  try {
    await flushSave()
    await callTool('export', 'session_update', {
      sessionId: sessionId.value,
      included: { [item.index]: !item.included },
    })
    await refresh()
  } catch (error) {
    notifyError(error)
  } finally {
    busy.value = false
  }
}

async function setAll(value: boolean) {
  if (busy.value) return
  busy.value = true
  try {
    await flushSave()
    const included: Record<string, boolean> = {}
    for (const item of items.value) included[String(item.index)] = value
    await callTool('export', 'session_update', { sessionId: sessionId.value, included })
    await refresh()
  } catch (error) {
    notifyError(error)
  } finally {
    busy.value = false
  }
}

async function reocr(item: SessionItem) {
  handled.value = ''
  try {
    await flushSave()
    await job.start('export', 'start_ocr', {
      sessionId: sessionId.value,
      indexes: [item.index],
    })
  } catch (error) {
    notifyError(error)
  }
}

async function copyText(item: SessionItem) {
  try {
    const text = draftIndex.value === item.index ? draftText.value : item.text
    await invoke('clipboard_write', text || '')
    notify('success', t('export.review.copied'))
  } catch (error) {
    notifyError(error)
  }
}

async function openPng(item: SessionItem) {
  try {
    await invoke('open_path', item.png)
  } catch (error) {
    notifyError(error)
  }
}

watch(
  () => job.snapshot.value?.status,
  async (status) => {
    const snapshot = job.snapshot.value
    if (!snapshot || status === 'running' || handled.value === snapshot.id) return
    handled.value = snapshot.id
    if (snapshot.status === 'failed') {
      notifyError({
        message: snapshot.error?.message || t('export.job.failed'),
        detail: snapshot.error?.detail,
      })
      return
    }
    if (snapshot.status === 'done') {
      await refresh()
      if (selected.value) {
        draftIndex.value = selected.value.index
        draftText.value = selected.value.text ?? ''
        dirty.value = false
        saveState.value = 'saved'
      }
      notify('success', t('export.review.reocrDone'))
    }
  },
)
</script>

<template>
  <div class="review">
    <section class="panel grid-panel">
      <div class="panel-head">
        <div class="head-left">
          <span>{{ t('export.review.title') }}</span>
          <span class="muted">{{ props.payload.title }}</span>
        </div>
        <div class="row">
          <span class="badge brand">{{ t('export.review.total', { n: stats.total }) }}</span>
          <span class="badge">{{ t('export.review.included', { n: stats.included }) }}</span>
          <span class="badge">{{ t('export.review.textCount', { n: stats.textCount }) }}</span>
          <span class="badge warn">{{ t('export.review.imageCount', { n: stats.imageCount }) }}</span>
          <span class="badge warn" v-if="stats.formula + stats.table + stats.image">
            {{ t('export.review.needCheck', { n: stats.formula + stats.table + stats.image }) }}
          </span>
          <span class="badge danger" v-if="stats.excluded">
            {{ t('export.review.excluded', { n: stats.excluded }) }}
          </span>
        </div>
      </div>

      <div class="filters">
        <div class="tabs">
          <button class="tab" :class="{ active: filter === 'all' }" @click="filter = 'all'">
            {{ t('export.review.filterAll') }}
          </button>
          <button class="tab" :class="{ active: filter === 'check' }" @click="filter = 'check'">
            {{ t('export.review.filterCheck') }}
          </button>
          <button class="tab" :class="{ active: filter === 'excluded' }" @click="filter = 'excluded'">
            {{ t('export.review.filterExcluded') }}
          </button>
        </div>
        <div class="row">
          <button class="btn sm" :disabled="busy" @click="setAll(true)">
            {{ t('export.review.selectAll') }}
          </button>
          <button class="btn sm" :disabled="busy" @click="setAll(false)">
            {{ t('export.review.selectNone') }}
          </button>
        </div>
      </div>

      <div class="grid-body">
        <div v-if="!paged.length" class="empty">{{ t('export.review.empty') }}</div>
        <div class="grid">
          <article
            v-for="item in paged"
            :key="item.index"
            class="card"
            :class="{ selected: selected?.index === item.index, excluded: !item.included }"
            @click="selectItem(item)"
          >
            <div class="thumb">
              <img :src="mediaUrl(item.png, 320)" loading="lazy" :alt="`第${item.index}题`" />
              <span class="idx mono">#{{ item.index }}</span>
              <button
                class="toggle"
                :class="{ on: item.included }"
                :title="item.included ? t('export.review.exclude') : t('export.review.include')"
                @click.stop="toggle(item)"
              >
                {{ item.included ? '✓' : '✕' }}
              </button>
            </div>
            <div class="meta">
              <span class="kind">{{ item.kind }}</span>
              <span v-if="item.exportMode === 'text'" class="badge">
                {{ t('export.review.mode.text') }}
              </span>
              <span v-else-if="item.exportMode === 'image'" class="badge warn">
                {{ t('export.review.mode.image') }}
              </span>
              <span v-for="tag in item.tags" :key="tag" class="badge warn">{{ tagLabel(tag) }}</span>
              <span v-if="item.ocrError" class="badge danger">{{ t('export.review.ocrError') }}</span>
            </div>
          </article>
        </div>
      </div>

      <div class="pager">
        <button class="btn sm" :disabled="page <= 1" @click="page -= 1">
          {{ t('export.review.prev') }}
        </button>
        <span class="muted mono">{{ page }} / {{ totalPages }}</span>
        <button class="btn sm" :disabled="page >= totalPages" @click="page += 1">
          {{ t('export.review.next') }}
        </button>
        <div class="spacer" />
        <button class="btn" @click="goBack">{{ t('export.review.back') }}</button>
        <button class="btn primary" :disabled="!stats.included" @click="goExport">
          {{ t('export.review.toExport') }}
        </button>
      </div>
    </section>

    <section class="panel detail-panel">
      <div class="panel-head">
        <span>{{ t('export.review.detail') }}</span>
        <span v-if="selected" class="mono">#{{ selected.index }}</span>
      </div>

      <div v-if="selected" class="detail-body">
        <div class="detail-img">
          <img :src="mediaUrl(selected.png, 900)" :alt="`第${selected.index}题`" />
        </div>

        <div class="row-wrap">
          <span class="badge">{{ selected.kind }}</span>
          <span v-for="tag in selected.tags" :key="tag" class="badge warn">
            {{ tagLabel(tag) }}
          </span>
          <span v-if="selected.ocrError" class="badge danger">{{ selected.ocrError }}</span>
          <button class="btn sm" @click="openPng(selected)">{{ t('export.review.openImage') }}</button>
          <button class="btn sm" :disabled="job.running.value" @click="reocr(selected)">
            {{ t('export.review.reocr') }}
          </button>
          <button class="btn sm" @click="copyText(selected)">{{ t('export.review.copy') }}</button>
        </div>

        <div class="editor">
          <div class="editor-head">
            <span>{{ t('export.review.textEditor') }}</span>
            <span class="state" :class="saveState">{{ saveStateLabel }}</span>
          </div>
          <textarea
            v-model="draftText"
            class="text-editor"
            spellcheck="false"
            :placeholder="t('export.review.noText')"
            @input="onTextInput"
            @blur="flushSave"
          />
          <div class="row-wrap mode-row">
            <span class="muted">{{ t('export.review.renderMode') }}</span>
            <div class="segmented small">
              <button
                v-for="mode in ['auto', 'text', 'image']"
                :key="mode"
                class="seg"
                :class="{ active: (selected.exportMode || 'auto') === mode }"
                @click="setMode(mode)"
              >
                {{ modeLabel(mode) }}
              </button>
            </div>
            <span class="hint">
              {{ t('export.review.effective', { mode: modeLabel(effectiveMode(selected)) }) }}
            </span>
          </div>
          <div class="row">
            <button class="btn sm" :disabled="!dirty" @click="flushSave">
              {{ t('export.review.saveText') }}
            </button>
            <span class="hint">{{ t('export.review.autoSaveHint') }}</span>
          </div>
        </div>

        <div v-if="job.running.value || job.terminal.value" class="job">
          <ProgressBar :progress="job.progress.value" />
          <LogConsole class="job-log" :logs="job.logs.value" />
        </div>
      </div>
      <div v-else class="empty">{{ t('export.review.pickOne') }}</div>
    </section>
  </div>
</template>

<style scoped>
.review {
  height: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 12px;
  min-height: 0;
}

.grid-panel {
  min-height: 0;
}

.head-left {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.head-left .muted {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.filters {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--line);
}

.grid-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.card {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-2);
  overflow: hidden;
  cursor: pointer;
}

.card.selected {
  border-color: var(--brand-dim);
  box-shadow: 0 0 0 2px var(--brand-soft);
}

.card.excluded {
  opacity: 0.55;
}

.thumb {
  position: relative;
  height: 96px;
  background: var(--bg);
  display: grid;
  place-items: center;
  overflow: hidden;
}

.thumb img {
  max-width: 100%;
  max-height: 100%;
}

.idx {
  position: absolute;
  left: 6px;
  top: 6px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(11, 15, 24, 0.75);
  color: var(--text);
  font-size: 10px;
}

.toggle {
  position: absolute;
  right: 6px;
  top: 6px;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  border: 1px solid var(--line-strong);
  background: rgba(11, 15, 24, 0.75);
  color: var(--muted);
  cursor: pointer;
}

.toggle.on {
  background: var(--brand);
  border-color: var(--brand);
  color: #04241f;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 6px 8px;
  font-size: 11px;
}

.kind {
  color: var(--muted);
}

.pager {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--line);
}

.detail-panel {
  min-height: 0;
}

.detail-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-img {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--bg);
  overflow: hidden;
  max-height: 42%;
}

.detail-img img {
  display: block;
  width: 100%;
}

.editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--muted);
  font-size: 11px;
}

.state.saved {
  color: var(--ok);
}
.state.saving {
  color: var(--muted);
}
.state.unsaved {
  color: var(--warn);
}
.state.error {
  color: var(--danger);
}

.text-editor {
  width: 100%;
  min-height: 180px;
  max-height: 320px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.8;
  resize: vertical;
  outline: none;
}

.text-editor:focus {
  border-color: var(--brand-dim);
  box-shadow: 0 0 0 3px var(--brand-soft);
}

.mode-row {
  gap: 8px;
}

.segmented {
  display: inline-flex;
  gap: 3px;
  padding: 3px;
  background: var(--surface-2);
  border-radius: var(--radius-sm);
}

.seg {
  height: 26px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-size: 11px;
}

.seg.active {
  background: var(--surface-3);
  border-color: var(--line-strong);
  color: var(--text);
}

.job {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.job-log {
  height: 160px;
}

@media (max-width: 1200px) {
  .review {
    grid-template-columns: minmax(0, 1fr) 360px;
  }
  .grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
