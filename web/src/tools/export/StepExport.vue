<!--
  StepExport.vue —— 第③步：导出 Word

  负责：确认文件名 / 覆盖策略，导出前分页预览将要生成的 Word，
  启动导出任务，展示进度与结果；完成后可打开文件或所在目录。

  预览由后端 export.preview_word 生成（与真正写 Word 共用同一份计划），
  这里把内容块按 A4 高度实测分页：每页固定高度、按块装填，长文档不会
  再出现「内容越过页底、压在阴影上」的问题。
-->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

import { callTool, invoke } from '../../platform/bridge'
import { t } from '../../platform/i18n'
import { useJob } from '../../platform/jobs'
import { mediaUrl } from '../../platform/media'
import { notify, notifyError } from '../../platform/toast'
import type { SessionPayload, WordPreview } from '../../platform/types'
import LogConsole from '../../ui/LogConsole.vue'
import ProgressBar from '../../ui/ProgressBar.vue'

const props = defineProps<{ payload: SessionPayload }>()
const emit = defineEmits<{ (e: 'back'): void; (e: 'reset'): void }>()

const filename = ref(props.payload.docxName)
const overwrite = ref(false)
const result = ref<{ path: string; name: string; textCount: number; imageCount: number; skipped: number[] } | null>(null)
const job = useJob()
const handled = ref('')
const existsHint = ref(false)

// ------ 导出前预览 ------ //
const preview = ref<WordPreview | null>(null)
const previewLoading = ref(false)
const rightTab = ref<'log' | 'preview'>('log')

// 预览排版比例：1 厘米 = 36 像素（约 96dpi 的 0.95 倍，宽度放得进右栏）
const PX_PER_CM = 36

interface PreviewBlock {
  kind: 'title' | 'text' | 'image'
  key: string
  text?: string
  src?: string
  alt?: string
}

/** 把题目列表摊平成「标题 / 正文 / 原图」块，分页只认这三种块。 */
const blocks = computed<PreviewBlock[]>(() => {
  const list: PreviewBlock[] = []
  const data = preview.value
  if (!data) return list
  for (const question of data.questions) {
    list.push({ kind: 'title', key: `t-${question.index}`, text: question.title })
    if (question.mode === 'image') {
      list.push({
        kind: 'image',
        key: `i-${question.index}`,
        src: mediaUrl(question.png, 900),
        alt: question.title,
      })
    } else {
      question.paragraphs.forEach((paragraph, index) => {
        list.push({ kind: 'text', key: `p-${question.index}-${index}`, text: paragraph })
      })
    }
  }
  return list
})

const pages = ref<PreviewBlock[][]>([])
const overflow = ref(false)
const measureRef = ref<HTMLElement | null>(null)

const geom = computed(() => {
  const data = preview.value
  const widthCm = data?.page.widthCm ?? 21
  const heightCm = data?.page.heightCm ?? 29.7
  const marginCm = data?.page.marginCm ?? 2.54
  const width = Math.round(widthCm * PX_PER_CM)
  const height = Math.round(heightCm * PX_PER_CM)
  const padding = Math.round(marginCm * PX_PER_CM)
  return {
    width,
    height,
    padding,
    content: Math.max(40, height - padding * 2),
    fontFamily: `"${data?.font ?? '宋体'}", SimSun, serif`,
    fontSize: Math.round((data?.fontSize ?? 10.5) * 1.27),
  }
})

const pageStyle = computed(() => ({
  width: `${geom.value.width}px`,
  height: `${geom.value.height}px`,
  padding: `${geom.value.padding}px`,
  fontFamily: geom.value.fontFamily,
  fontSize: `${geom.value.fontSize}px`,
}))

const measureStyle = computed(() => ({
  width: `${geom.value.width}px`,
  padding: `${geom.value.padding}px`,
  fontFamily: geom.value.fontFamily,
  fontSize: `${geom.value.fontSize}px`,
}))

async function layoutPages() {
  if (!preview.value) {
    pages.value = []
    overflow.value = false
    return
  }
  await nextTick()
  try {
    await document.fonts?.ready
  } catch {
    // 字体接口不可用就直接量，差一点不影响分页结论
  }
  const box = measureRef.value
  if (!box) return
  const kids = Array.from(box.children).filter((el) =>
    el.classList.contains('blk'),
  ) as HTMLElement[]
  const heights = kids.map((el) => el.offsetHeight)
  const limit = geom.value.content
  const result: PreviewBlock[][] = []
  let current: PreviewBlock[] = []
  let used = 0
  let clipped = false

  for (let i = 0; i < blocks.value.length; i += 1) {
    const block = blocks.value[i]
    const height = heights[i] ?? 0
    // 标题要和下一块同页，避免页底只剩「第N题」；
    const glued = block.kind === 'title' ? heights[i + 1] ?? 0 : 0
    if (height > limit) clipped = true
    if (current.length && used + height + glued > limit) {
      result.push(current)
      current = []
      used = 0
    }
    current.push(block)
    used += Math.min(height, limit)
  }
  if (current.length) result.push(current)

  pages.value = result
  overflow.value = clipped
}

watch(
  preview,
  () => {
    pages.value = []
    void layoutPages()
  },
  { flush: 'post' },
)

// 预览生成时如果停在「运行日志」页，切回来要补一次分页
watch(rightTab, (tab) => {
  if (tab === 'preview' && preview.value && !pages.value.length) {
    void layoutPages()
  }
})

async function loadPreview() {
  if (previewLoading.value) return
  previewLoading.value = true
  rightTab.value = 'preview'
  try {
    preview.value = await callTool<WordPreview>('export', 'preview_word', {
      sessionId: props.payload.session.id,
    })
  } catch (error) {
    notifyError(error)
  } finally {
    previewLoading.value = false
  }
}

watch(
  () => props.payload.session.id,
  () => {
    preview.value = null
    rightTab.value = 'log'
  },
)

// ------ 导出 ------ //
async function startExport() {
  result.value = null
  handled.value = ''
  existsHint.value = false
  try {
    await job.start('export', 'start_export', {
      sessionId: props.payload.session.id,
      filename: filename.value,
      overwrite: overwrite.value,
    })
  } catch (error: any) {
    if (error?.code === 'FILE_EXISTS') {
      existsHint.value = true
      notify('error', t('export.export.fileExists'), error.detail)
      return
    }
    notifyError(error)
  }
}

async function openResult() {
  if (!result.value) return
  try {
    await invoke('open_path', result.value.path)
  } catch (error) {
    notifyError(error)
  }
}

async function openFolder() {
  try {
    await invoke('open_path', 'resources/word_output')
  } catch (error) {
    notifyError(error)
  }
}

watch(
  () => job.snapshot.value?.status,
  (status) => {
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
    if (snapshot.status === 'done' && snapshot.result) {
      result.value = snapshot.result as any
      notify('success', t('export.export.done'), String(snapshot.result.name || ''))
    }
  },
)
</script>

<template>
  <div class="export">
    <section class="panel form-panel">
      <div class="panel-head">
        <span>{{ t('export.export.title') }}</span>
        <span class="mono">{{ props.payload.session.scope.mode === 'paper' ? props.payload.session.scope.paper : props.payload.session.scope.pngType }}</span>
      </div>
      <div class="panel-body">
        <div class="summary">
          <div class="stat">
            <span class="num mono">{{ props.payload.stats.included }}</span>
            <span class="muted">{{ t('export.export.included') }}</span>
          </div>
          <div class="stat">
            <span class="num mono">{{ props.payload.stats.textCount }}</span>
            <span class="muted">{{ t('export.export.textQuestions') }}</span>
          </div>
          <div class="stat">
            <span class="num mono">{{ props.payload.stats.imageCount }}</span>
            <span class="muted">{{ t('export.export.imageQuestions') }}</span>
          </div>
          <div class="stat">
            <span class="num mono">{{ props.payload.stats.excluded }}</span>
            <span class="muted">{{ t('export.export.excluded') }}</span>
          </div>
        </div>

        <div class="field">
          <label class="field-label">{{ t('export.export.filename') }}</label>
          <input v-model="filename" class="input" :disabled="job.running.value" />
          <div class="hint">{{ t('export.export.filenameHint') }}</div>
        </div>

        <label class="switch">
          <input v-model="overwrite" type="checkbox" :disabled="job.running.value" />
          <span>{{ t('export.export.overwrite') }}</span>
        </label>
        <div v-if="existsHint" class="hint danger">{{ t('export.export.fileExistsHint') }}</div>

        <div class="actions">
          <button class="btn" :disabled="job.running.value" @click="emit('back')">
            {{ t('export.export.back') }}
          </button>
          <button class="btn" :disabled="job.running.value || previewLoading" @click="loadPreview">
            {{ previewLoading ? t('export.export.previewLoading') : t('export.export.preview') }}
          </button>
          <button class="btn primary" :disabled="job.running.value" @click="startExport">
            {{ t('export.action.export') }}
          </button>
          <button v-if="job.running.value" class="btn danger" @click="job.cancel()">
            {{ t('action.cancel') }}
          </button>
        </div>

        <div v-if="result" class="result">
          <div class="success-title">{{ t('export.export.done') }}</div>
          <div class="mono path">{{ result.name }}</div>
          <div class="hint">
            {{ t('export.export.summary', { text: result.textCount, image: result.imageCount, skipped: result.skipped.length }) }}
          </div>
          <div class="row">
            <button class="btn" @click="openResult">{{ t('export.export.openFile') }}</button>
            <button class="btn" @click="openFolder">{{ t('export.export.openFolder') }}</button>
            <button class="btn primary" @click="emit('reset')">
              {{ t('export.export.newTask') }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <section class="panel right">
      <div class="panel-head">
        <div class="tabs">
          <button class="tab" :class="{ active: rightTab === 'log' }" @click="rightTab = 'log'">
            {{ t('export.export.tabLog') }}
          </button>
          <button
            class="tab"
            :class="{ active: rightTab === 'preview' }"
            @click="rightTab = 'preview'"
          >
            {{ t('export.export.tabPreview') }}
          </button>
        </div>
        <span v-if="job.running.value" class="badge warn">{{ t('export.job.running') }}</span>
      </div>

      <div v-if="rightTab === 'log'" class="right-body">
        <ProgressBar v-if="job.running.value || job.terminal.value" :progress="job.progress.value" />
        <LogConsole class="log" :logs="job.logs.value" :show-head="false" />
      </div>

      <div v-else class="right-body preview-body">
        <div v-if="previewLoading" class="empty">{{ t('export.export.previewLoading') }}</div>
        <div v-else-if="!preview" class="empty">{{ t('export.export.previewEmpty') }}</div>
        <template v-else>
          <div class="preview-head">
            <div class="row-wrap">
              <span class="badge brand">{{ preview.filename }}</span>
              <span class="badge">{{ t('export.export.previewSummary', { n: preview.total, text: preview.textCount, image: preview.imageCount }) }}</span>
              <span class="badge">{{ t('export.export.previewPages', { n: pages.length }) }}</span>
              <span v-if="preview.skipped.length" class="badge danger">
                {{ t('export.export.previewSkipped', { n: preview.skipped.length }) }}
              </span>
            </div>
            <div v-if="overflow" class="overflow-hint">
              {{ t('export.export.previewOverflow') }}
            </div>
            <div v-if="preview.warnings.length" class="warnings">
              <div class="warn-title">{{ t('export.export.previewWarnings') }}</div>
              <div
                v-for="(warning, i) in preview.warnings"
                :key="i"
                class="warn-line"
                :class="warning.level"
              >
                · {{ warning.text }}
              </div>
            </div>
          </div>

          <div class="page-wrap">
            <!-- 隐藏测量层：和正文同样的宽度/字体/内边距，只用来量每一块的高度 -->
            <div ref="measureRef" class="page measure" :style="measureStyle" aria-hidden="true">
              <div
                v-for="block in blocks"
                :key="`m-${block.key}`"
                class="blk"
                :class="block.kind"
              >
                <template v-if="block.kind === 'image'">
                  <img class="q-img" :src="block.src" :alt="block.alt" :style="{ maxHeight: `${geom.content}px` }" />
                </template>
                <template v-else>{{ block.text }}</template>
              </div>
            </div>

            <div
              v-for="(pageBlocks, pageIndex) in pages"
              :key="`page-${pageIndex}`"
              class="page sheet"
              :style="pageStyle"
            >
              <div
                v-for="block in pageBlocks"
                :key="block.key"
                class="blk"
                :class="block.kind"
              >
                <template v-if="block.kind === 'image'">
                  <img class="q-img" :src="block.src" :alt="block.alt" :style="{ maxHeight: `${geom.content}px` }" />
                </template>
                <template v-else>{{ block.text }}</template>
              </div>
              <div class="page-no">{{ pageIndex + 1 }} / {{ pages.length }}</div>
            </div>
          </div>

          <div class="preview-foot hint">{{ t('export.export.previewHint') }}</div>
        </template>
      </div>
    </section>
  </div>
</template>

<style scoped>
.export {
  height: 100%;
  display: grid;
  grid-template-columns: 420px minmax(0, 1fr);
  gap: 12px;
  min-height: 0;
}

.form-panel .panel-body {
  overflow: auto;
}

.summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-2);
}

.stat .num {
  font-size: 22px;
  color: var(--brand);
}

.stat .muted {
  font-size: 11px;
}

.switch {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 12px;
  margin: 8px 0;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.result {
  margin-top: 18px;
  padding: 12px;
  border: 1px solid rgba(89, 212, 153, 0.35);
  border-radius: 10px;
  background: rgba(89, 212, 153, 0.06);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.success-title {
  color: var(--ok);
  font-weight: 600;
}

.path {
  font-size: 11px;
  word-break: break-all;
}

.right-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
}

.log {
  flex: 1;
}

.tabs {
  display: flex;
  gap: 4px;
}

.tab {
  height: 26px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-size: 12px;
}

.tab.active {
  background: var(--surface-3);
  border-color: var(--line-strong);
  color: var(--text);
}

/* ------ 版式预览 ------ */
.preview-body {
  overflow: hidden;
}

.preview-head {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 0 0 auto;
}

.warnings {
  padding: 8px 10px;
  border: 1px solid rgba(242, 193, 78, 0.35);
  border-radius: 8px;
  background: rgba(242, 193, 78, 0.06);
  font-size: 12px;
}

.warn-title {
  color: var(--warn);
  margin-bottom: 4px;
}

.warn-line {
  color: var(--muted);
  line-height: 1.6;
}

.warn-line.error {
  color: var(--danger);
}

.overflow-hint {
  padding: 6px 10px;
  border: 1px solid rgba(255, 95, 109, 0.4);
  border-radius: 8px;
  background: rgba(255, 95, 109, 0.08);
  color: var(--danger);
  font-size: 12px;
}

.page-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 4px 0 14px;
}

.page {
  flex: 0 0 auto;
  background: #fff;
  color: #1a1a1a;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.35);
  border-radius: 2px;
  box-sizing: border-box;
  line-height: 1.8;
  overflow-wrap: break-word;
  position: relative;
  overflow: hidden;
}

/* 测量层不占位、不显示，只用来量高度 */
.page.measure {
  position: absolute;
  left: -100000px;
  top: 0;
  height: auto;
  min-height: 0;
  box-shadow: none;
  overflow: visible;
}

.blk.title {
  padding: 14px 0 4px;
  font-weight: 700;
}

.blk.text {
  padding: 0 0 2px;
}

.blk.image {
  padding: 4px 0 2px;
  display: flex;
  justify-content: center;
}

.blk:first-child {
  padding-top: 0;
}

.q-img {
  display: block;
  max-width: 100%;
}

.page-no {
  position: absolute;
  right: 10px;
  bottom: 6px;
  color: #9a9a9a;
  font-size: 10px;
}

.preview-foot {
  flex: 0 0 auto;
  margin: 0;
}
</style>
