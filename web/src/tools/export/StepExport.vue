<!--
  StepExport.vue —— 第③步：导出 Word

  负责：确认文件名 / 覆盖策略，启动导出任务，展示进度与结果；
  完成后可打开文件或所在目录。
-->
<script setup lang="ts">
import { ref, watch } from 'vue'

import { invoke } from '../../platform/bridge'
import { t } from '../../platform/i18n'
import { useJob } from '../../platform/jobs'
import { notify, notifyError } from '../../platform/toast'
import type { SessionPayload } from '../../platform/types'
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
        <span>{{ t('export.capture.logTitle') }}</span>
        <span v-if="job.running.value" class="badge warn">{{ t('export.job.running') }}</span>
      </div>
      <div class="right-body">
        <ProgressBar v-if="job.running.value || job.terminal.value" :progress="job.progress.value" />
        <LogConsole class="log" :logs="job.logs.value" :show-head="false" />
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
</style>
