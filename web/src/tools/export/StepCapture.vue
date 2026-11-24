<!--
  StepCapture.vue —— 第①步：采集

  负责：
  - 选择整卷 / 单题型，填卷名、题型、题量、是否清空旧图；
  - 环境自检、连接模拟器、预检（截一屏画识别框）、开始采集、取消；
  - 采集任务内部会自动接着 OCR，完成后 emit('captured', sessionId)。
-->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { callTool, invoke } from '../../platform/bridge'
import { t } from '../../platform/i18n'
import { useJob } from '../../platform/jobs'
import { mediaUrl } from '../../platform/media'
import { getSettings, loadSettings } from '../../platform/settings'
import { notify, notifyError } from '../../platform/toast'
import type { EnvStatus, ProbeCard, ProbeResult } from '../../platform/types'
import LogConsole from '../../ui/LogConsole.vue'
import ProgressBar from '../../ui/ProgressBar.vue'

const emit = defineEmits<{
  (e: 'captured', sessionId: string): void
  (e: 'openHistory'): void
}>()

const job = useJob()
const env = ref<EnvStatus | null>(null)
const probeResult = ref<ProbeResult | null>(null)
const papers = ref<string[]>([])
const handled = ref('')

const cfg = computed(() => getSettings('export'))
const types = computed(() => splitList(cfg.value.capture?.types))

const mode = ref<'paper' | 'type'>('paper')
const paper = ref('')
const pngType = ref('')
const pages = ref(200)
const clearOld = ref(false)
const connectAddress = ref('127.0.0.1:16384')

function splitList(value: unknown): string[] {
  const text = String(value || '')
  const items = text
    .replace(/，/g, ',')
    .replace(/、/g, ',')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
  return items.length ? items : ['选择题', '分析题', '画图题', '计算题']
}

async function loadConfig() {
  if (!Object.keys(cfg.value).length) {
    try {
      await loadSettings('export')
    } catch (error) {
      notifyError(error)
    }
  }
  pages.value = Number(cfg.value.capture?.pages ?? 200)
  connectAddress.value = String(cfg.value.device?.connectAddress ?? '127.0.0.1:16384')
  pngType.value = types.value[0] ?? ''
}

async function loadHistory() {
  try {
    const data = await callTool<{ inventory: { papers: { name: string }[] } }>(
      'export',
      'history',
    )
    papers.value = (data.inventory?.papers ?? []).map((item) => item.name)
  } catch {
    // 历史读取失败不影响采集
  }
}

// ------ 环境 / 设备 ------ //
async function refreshEnv() {
  try {
    env.value = await invoke<EnvStatus>('env_check')
    // 顶栏/表单里的状态灯已经能看出结果，这里只在 OCR 不可用时提醒
    if (!env.value.tesseract.ok) {
      notify('error', t('export.env.ocrBad'), env.value.tesseract.error)
    }
  } catch (error) {
    notifyError(error)
  }
}

async function openData() {
  try {
    await invoke('storage_open_dir')
  } catch (error) {
    notifyError(error)
  }
}

async function connectDevice() {
  try {
    const result = await invoke<{ devices: string[]; output: string }>(
      'device_connect',
      connectAddress.value,
    )
    notify(
      result.devices.length ? 'success' : 'error',
      result.devices.length
        ? t('export.device.connected', { n: result.devices.length })
        : t('export.device.noDevice'),
      result.output || result.devices.join(', '),
    )
  } catch (error) {
    notifyError(error)
  }
}

// ------ 任务 ------ //
async function startProbe() {
  probeResult.value = null
  handled.value = ''
  try {
    await job.start('export', 'probe')
  } catch (error) {
    notifyError(error)
  }
}

async function startCapture() {
  if (mode.value === 'paper' && !paper.value.trim()) {
    notify('error', t('export.capture.needPaper'))
    return
  }
  if (mode.value === 'type' && !pngType.value) {
    notify('error', t('export.capture.needType'))
    return
  }
  handled.value = ''
  try {
    await job.start('export', 'start_capture', {
      mode: mode.value,
      paper: paper.value.trim(),
      pngType: pngType.value,
      pages: Number(pages.value) || 1,
      clearOld: clearOld.value,
    })
  } catch (error) {
    notifyError(error)
  }
}

async function cancelJob() {
  try {
    await job.cancel()
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
    if (snapshot.status === 'cancelled') {
      notify('info', t('export.job.cancelled'))
      return
    }

    if (snapshot.kind === 'probe' && snapshot.result) {
      probeResult.value = snapshot.result as unknown as ProbeResult
      notify('success', t('export.probe.done', { n: probeResult.value.cards.length }))
    }
    if (snapshot.kind === 'capture' && snapshot.result?.sessionId) {
      emit('captured', String(snapshot.result.sessionId))
    }
  },
)

// 预检框：把虚拟机像素坐标换算成百分比
function boxStyle(card: ProbeCard) {
  const height = probeResult.value?.height || 900
  return {
    top: `${(card.headerTop / height) * 100}%`,
    height: `${Math.max(1, (card.bottom - card.headerTop) / height) * 100}%`,
  }
}

onMounted(async () => {
  await loadConfig()
  await loadHistory()
  await refreshEnv()
})
</script>

<template>
  <div class="capture">
    <!-- 左：参数 -->
    <section class="panel form-panel">
      <div class="panel-head">
        <span>{{ t('export.capture.title') }}</span>
        <span class="muted">{{ cfg.device?.connectAddress || '' }}</span>
      </div>
      <div class="panel-body">
        <div class="field">
          <label class="field-label">{{ t('export.capture.mode') }}</label>
          <div class="segmented">
            <button
              class="seg"
              :class="{ active: mode === 'paper' }"
              @click="mode = 'paper'"
            >
              {{ t('export.capture.modePaper') }}
            </button>
            <button class="seg" :class="{ active: mode === 'type' }" @click="mode = 'type'">
              {{ t('export.capture.modeType') }}
            </button>
          </div>
        </div>

        <div v-if="mode === 'paper'" class="field">
          <label class="field-label">
            <span>{{ t('export.capture.paper') }}</span>
            <button class="btn ghost sm" @click="emit('openHistory')">
              {{ t('export.capture.pickHistory') }}
            </button>
          </label>
          <input v-model="paper" class="input" list="paper-list" :placeholder="t('export.capture.paperPh')" />
          <datalist id="paper-list">
            <option v-for="name in papers" :key="name" :value="name" />
          </datalist>
          <div class="hint">{{ t('export.capture.paperHint') }}</div>
        </div>

        <div v-else class="field">
          <label class="field-label">{{ t('export.capture.type') }}</label>
          <select v-model="pngType" class="input">
            <option v-for="name in types" :key="name" :value="name">{{ name }}</option>
          </select>
          <div class="hint">{{ t('export.capture.typeHint') }}</div>
        </div>

        <div class="field-row">
          <div class="field">
            <label class="field-label">{{ t('export.capture.pages') }}</label>
            <input v-model.number="pages" class="input mono" type="number" min="1" max="5000" />
          </div>
          <div class="field">
            <label class="field-label">{{ t('export.capture.clearOld') }}</label>
            <label class="switch">
              <input v-model="clearOld" type="checkbox" :disabled="mode === 'paper'" />
              <span>{{ t('export.capture.clearOldHint') }}</span>
            </label>
          </div>
        </div>

        <div class="field">
          <label class="field-label">{{ t('export.capture.connectAddress') }}</label>
          <div class="path-field">
            <input v-model="connectAddress" class="input mono" />
            <button class="btn sm" @click="connectDevice">{{ t('export.action.connect') }}</button>
          </div>
        </div>

        <div class="actions">
          <button class="btn" :disabled="job.running.value" @click="refreshEnv">
            {{ t('export.action.env') }}
          </button>
          <button class="btn" :disabled="job.running.value" @click="startProbe">
            {{ t('export.action.probe') }}
          </button>
          <button
            class="btn primary"
            :disabled="job.running.value"
            @click="startCapture"
          >
            {{ t('export.action.capture') }}
          </button>
          <button v-if="job.running.value" class="btn danger" @click="cancelJob">
            {{ t('action.cancel') }}
          </button>
        </div>

        <div class="env">
          <span class="badge" :class="env?.adb?.devices?.length ? 'brand' : 'warn'">
            adb {{ env?.adb?.devices?.length ?? 0 }}
          </span>
          <span class="badge" :class="env?.tesseract?.ok ? 'brand' : 'danger'">
            OCR {{ env?.tesseract?.ok ? 'OK' : '!' }}
          </span>
          <button class="btn ghost sm" @click="openData">
            {{ t('export.action.openData') }}
          </button>
        </div>

        <div class="hint">{{ t('export.capture.warmupHint') }}</div>
      </div>
    </section>

    <!-- 右：预览 / 日志 -->
    <section class="panel right">
      <div class="panel-head">
        <span>{{ probeResult ? t('export.probe.title') : t('export.capture.logTitle') }}</span>
        <span v-if="job.running.value" class="badge warn">{{ t('export.job.running') }}</span>
      </div>

      <div class="right-body">
        <div v-if="probeResult" class="probe">
          <img :src="mediaUrl(probeResult.frame)" :alt="t('export.probe.title')" />
          <div
            v-for="card in probeResult.cards"
            :key="card.index"
            class="probe-box"
            :class="{ cut: !card.complete }"
            :style="boxStyle(card)"
          >
            <span class="probe-tag">
              #{{ card.number ?? '?' }} · {{ card.kind || t('export.probe.unknown') }}
            </span>
          </div>
        </div>

        <ProgressBar v-if="job.running.value || job.terminal.value" :progress="job.progress.value" />
        <LogConsole class="log" :logs="job.logs.value" :show-head="false" />

        <div v-if="job.snapshot.value?.artifacts?.length" class="thumbs">
          <img
            v-for="item in job.snapshot.value.artifacts.slice(-6)"
            :key="item.path"
            :src="mediaUrl(item.path, 160)"
            :title="item.path"
          />
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.capture {
  height: 100%;
  display: grid;
  grid-template-columns: 380px minmax(0, 1fr);
  gap: 12px;
  min-height: 0;
}

.form-panel .panel-body {
  overflow: auto;
}

.right {
  min-height: 0;
}

.right-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
}

.segmented {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: var(--surface-2);
  border-radius: var(--radius-sm);
}

.seg {
  flex: 1;
  height: 30px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}

.seg.active {
  background: var(--surface-3);
  border-color: var(--line-strong);
  color: var(--text);
}

.switch {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 12px;
}

.path-field {
  display: flex;
  gap: 8px;
}

.path-field .input {
  flex: 1;
  min-width: 0;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 6px 0 12px;
}

.env {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 8px 0;
  border-top: 1px solid var(--line);
}

.probe {
  position: relative;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--bg);
  max-height: 46%;
}

.probe img {
  display: block;
  width: 100%;
}

.probe-box {
  position: absolute;
  left: 0;
  width: 100%;
  border-top: 2px solid var(--brand);
  border-bottom: 1px solid var(--brand);
  background: rgba(62, 224, 196, 0.08);
}

.probe-box.cut {
  border-color: var(--warn);
  background: rgba(242, 193, 78, 0.08);
}

.probe-tag {
  position: absolute;
  left: 8px;
  top: 2px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--surface);
  color: var(--brand);
  font-size: 10px;
}

.probe-box.cut .probe-tag {
  color: var(--warn);
}

.log {
  flex: 1;
  min-height: 120px;
}

.thumbs {
  display: flex;
  gap: 6px;
  overflow: hidden;
}

.thumbs img {
  height: 52px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--bg);
}
</style>
