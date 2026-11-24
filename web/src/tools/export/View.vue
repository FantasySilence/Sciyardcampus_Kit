<!--
  View.vue（采集导出）

  三步向导：
  ① 采集（StepCapture）→ ② 预览检查（StepReview）→ ③ 导出（StepExport）
  以及工具内的「历史」面板（HistoryPanel）。

  父组件只负责当前步骤与当前会话（SessionPayload）：
  - 采集完成拿到 sessionId，向后端取会话后进入第 ② 步；
  - 预览页每次剔除/重识别后把新会话回传；
  - 历史项点击后转成会话，同样进入第 ② 步。
-->
<script setup lang="ts">
import { ref } from 'vue'

import { callTool } from '../../platform/bridge'
import { t } from '../../platform/i18n'
import { notifyError } from '../../platform/toast'
import type { HistoryEntry, SessionPayload, ToolDef } from '../../platform/types'
import HistoryPanel from './HistoryPanel.vue'
import StepCapture from './StepCapture.vue'
import StepExport from './StepExport.vue'
import StepReview from './StepReview.vue'

defineProps<{ tool: ToolDef }>()

const step = ref<1 | 2 | 3>(1)
const payload = ref<SessionPayload | null>(null)
const tab = ref<'wizard' | 'history'>('wizard')
const loading = ref(false)

async function onCaptured(sessionId: string) {
  await openSession(sessionId)
}

async function openSession(sessionId: string) {
  loading.value = true
  try {
    payload.value = await callTool<SessionPayload>('export', 'session_get', { sessionId })
    step.value = 2
    tab.value = 'wizard'
  } catch (error) {
    notifyError(error)
  } finally {
    loading.value = false
  }
}

async function openHistory(entry: HistoryEntry) {
  loading.value = true
  try {
    const data = entry.id
      ? await callTool<SessionPayload>('export', 'session_get', { sessionId: entry.id })
      : await callTool<SessionPayload>('export', 'session_get', { ...entry.scope })
    payload.value = data
    step.value = 2
    tab.value = 'wizard'
  } catch (error) {
    notifyError(error)
  } finally {
    loading.value = false
  }
}

function onUpdated(next: SessionPayload) {
  payload.value = next
}

function resetWizard() {
  step.value = 1
  payload.value = null
  tab.value = 'wizard'
}
</script>

<template>
  <div class="tool">
    <header class="tool-head">
      <div class="steps">
        <button
          class="step"
          :class="{ active: step === 1 }"
          :disabled="tab === 'history'"
          @click="step = 1"
        >
          <span class="num">1</span>
          {{ t('export.step.capture') }}
        </button>
        <span class="arrow">→</span>
        <button class="step" :class="{ active: step === 2 }" :disabled="!payload" @click="step = 2">
          <span class="num">2</span>
          {{ t('export.step.review') }}
        </button>
        <span class="arrow">→</span>
        <button class="step" :class="{ active: step === 3 }" :disabled="!payload" @click="step = 3">
          <span class="num">3</span>
          {{ t('export.step.export') }}
        </button>
      </div>

      <div class="tabs">
        <button class="tab" :class="{ active: tab === 'wizard' }" @click="tab = 'wizard'">
          {{ t('export.tab.wizard') }}
        </button>
        <button class="tab" :class="{ active: tab === 'history' }" @click="tab = 'history'">
          {{ t('export.tab.history') }}
        </button>
      </div>
    </header>

    <div v-if="loading" class="panel loading">
      <div class="empty">{{ t('export.loadingSession') }}</div>
    </div>

    <template v-else>
      <div v-if="tab === 'history'" class="body">
        <HistoryPanel @open="openHistory" />
      </div>

      <div v-else class="body">
        <StepCapture
          v-if="step === 1"
          @captured="onCaptured"
          @openHistory="tab = 'history'"
        />
        <StepReview
          v-else-if="step === 2 && payload"
          :payload="payload"
          @updated="onUpdated"
          @export="step = 3"
          @back="step = 1"
          @reset="resetWizard"
        />
        <StepExport
          v-else-if="step === 3 && payload"
          :payload="payload"
          @back="step = 2"
          @reset="resetWizard"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.tool {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.tool-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.steps {
  display: flex;
  align-items: center;
  gap: 6px;
}

.step {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  color: var(--muted);
  cursor: pointer;
}

.step:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.step.active {
  border-color: var(--brand-dim);
  background: var(--brand-soft);
  color: var(--brand);
}

.num {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--surface-3);
  font-size: 11px;
}

.step.active .num {
  background: var(--brand);
  color: #04241f;
}

.arrow {
  color: var(--muted);
}

.body {
  flex: 1;
  min-height: 0;
}

.loading {
  flex: 1;
}
</style>
