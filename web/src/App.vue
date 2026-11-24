<!--
  App.vue —— 应用外壳

  负责：
  - 启动时通过 pywebview 桥取 app_state（版本、语言、主题、工具清单、数据目录、媒体地址）；
  - 左侧工具轨、顶部命令栏、工作区、设置抽屉、关于弹窗、Toast；
  - 环境状态灯：adb / Tesseract，点击设置可改路径；
  - 全局快捷键：Ctrl+1..9 切换工具、Ctrl+, 打开设置、Esc 关闭浮层。
-->
<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref } from 'vue'

import { invoke, waitReady } from './platform/bridge'
import { languages, locale, setLocale, t } from './platform/i18n'
import { setMediaBase } from './platform/media'
import { loadSettings, settings as settingsCache } from './platform/settings'
import { applyTheme, theme, toggleTheme } from './platform/theme'
import { notify, notifyError } from './platform/toast'
import { viewFor } from './platform/tools'
import type { AppState, EnvStatus, ToolDef } from './platform/types'
import AboutDialog from './shell/AboutDialog.vue'
import SettingsDrawer from './shell/SettingsDrawer.vue'
import StatChip from './ui/StatChip.vue'
import ToastHost from './ui/ToastHost.vue'

const state = ref<AppState | null>(null)
const bootError = ref('')
const activeId = ref('')
const drawer = ref(false)
const aboutOpen = ref(false)
const env = ref<EnvStatus | null>(null)

const viewCache = new Map<string, ReturnType<typeof defineAsyncComponent>>()

function componentFor(id: string) {
  if (!viewCache.has(id)) {
    const loader = viewFor(id)
    if (loader) viewCache.set(id, defineAsyncComponent(loader as never))
  }
  return viewCache.get(id) ?? null
}

const activeTool = computed<ToolDef | null>(
  () => state.value?.tools.find((tool) => tool.id === activeId.value) ?? null,
)
const activeComponent = computed(() => (activeId.value ? componentFor(activeId.value) : null))

// ------ 图标 ------ //
const ICONS: Record<string, string> = {
  capture:
    '<rect x="3.5" y="5" width="17" height="14" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M7 9h6M7 12h8M7 15h5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="17.2" cy="8.2" r="1.5" fill="currentColor"/>',
  publish:
    '<path d="M4 10v4a1 1 0 0 0 1 1h2l6 4V5L7 9H5a1 1 0 0 0-1 1Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M16 8.5a5 5 0 0 1 0 7M18.6 6a8.4 8.4 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  exam:
    '<rect x="4.5" y="4.5" width="15" height="16" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M8.5 8.8h7M8.5 12h4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M8.4 16.4l1.8 1.8 3.6-3.8" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>',
  regular:
    '<rect x="3.6" y="5.2" width="16.8" height="14.6" rx="2.4" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M3.6 9.4h16.8M8 3.4v3.2M16 3.4v3.2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M7.4 13h4M7.4 16.2h7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
  soon:
    '<path d="M12 3.6l1.8 4.5 4.6 1.8-4.6 1.8L12 16.2l-1.8-4.5L5.6 9.9l4.6-1.8Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M17.9 15.9l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7Z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>',
  info: '<circle cx="12" cy="12" r="8.6" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 11v5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="12" cy="8" r="1.1" fill="currentColor"/>',
  gear: '<circle cx="12" cy="12" r="3.4" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
}

function icon(name: string): string {
  return ICONS[name] ?? ICONS.capture
}

const languageLabels: Record<string, string> = {
  zh_CN: '简体中文',
  en: 'English',
}

// ------ 环境状态灯 ------ //
const adbChip = computed(() => {
  const adb = env.value?.adb
  if (!adb || !adb.found) return { state: 'error' as const, label: t('env.adbMissing'), detail: adb?.error || '' }
  if (!adb.devices.length) return { state: 'warn' as const, label: t('env.adbNoDevice'), detail: adb.path }
  return {
    state: 'ok' as const,
    label: t('env.adbReady', { n: adb.devices.length }),
    detail: `${adb.path}\n${adb.devices.join('\n')}`,
  }
})

const ocrChip = computed(() => {
  const ocr = env.value?.tesseract
  if (!ocr) return { state: 'muted' as const, label: t('env.ocrUnknown'), detail: '' }
  if (!ocr.ok) return { state: 'error' as const, label: t('env.ocrMissing'), detail: ocr.error || ocr.missing.join(', ') }
  return {
    state: 'ok' as const,
    label: t('env.ocrReady'),
    detail: `${ocr.path}\n${ocr.version}\n${ocr.langs.join(', ')}`,
  }
})

async function refreshEnv() {
  try {
    env.value = await invoke<EnvStatus>('env_check')
  } catch {
    // 环境自检失败不阻塞界面；状态灯会保持灰色
  }
}

// ------ 事件 ------ //
async function selectTool(id: string) {
  if (!state.value?.tools.some((tool) => tool.id === id)) return
  activeId.value = id
  if (!settingsCache[id]) {
    try {
      await loadSettings(id)
    } catch (error) {
      notifyError(error)
    }
  }
  void invoke('app_set_pref', 'lastTool', id).catch(() => undefined)
}

async function changeLanguage(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  setLocale(value)
  try {
    await invoke('app_set_pref', 'language', value)
  } catch (error) {
    notifyError(error)
  }
}

/** 左轨「敬请期待」：只提示，不切换工具。 */
function onComingSoon() {
  notify('info', t('nav.comingSoon'), t('nav.comingSoonHint'))
}

async function onToggleTheme() {
  const next = toggleTheme()
  try {
    await invoke('app_set_pref', 'theme', next)
  } catch (error) {
    notifyError(error)
  }
}

function onKeydown(event: KeyboardEvent) {
  if (!state.value) return
  if (event.ctrlKey && event.key >= '1' && event.key <= '9') {
    const index = Number(event.key) - 1
    const tool = state.value.tools[index]
    if (tool) {
      event.preventDefault()
      void selectTool(tool.id)
    }
  }
  if (event.ctrlKey && event.key === ',') {
    event.preventDefault()
    drawer.value = true
  }
  if (event.key === 'Escape') {
    drawer.value = false
    aboutOpen.value = false
  }
}

// ------ 生命周期 ------ //
let envTimer = 0

onMounted(async () => {
  try {
    await waitReady()
    const data = await invoke<AppState>('app_state')
    state.value = data
    setMediaBase(data.mediaBase)
    setLocale(data.language)
    applyTheme(data.theme === 'light' ? 'light' : 'dark')
    const preferred = data.tools.find((tool) => tool.id === data.lastTool)
    await selectTool(preferred?.id ?? data.tools[0]?.id ?? '')
    await refreshEnv()
    // 每 20 秒刷新一次环境状态灯；任务运行中也不影响
    envTimer = window.setInterval(refreshEnv, 20000)
  } catch (error) {
    bootError.value = error instanceof Error ? error.message : String(error)
  }
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  if (envTimer) window.clearInterval(envTimer)
})
</script>

<template>
  <div v-if="state && activeTool" class="app">
    <!-- 左侧工具轨 -->
    <aside class="rail">
      <div class="mark" :title="t('app.name')">◆</div>
      <button
        v-for="tool in state.tools"
        :key="tool.id"
        class="rail-item"
        :class="{ active: tool.id === activeId }"
        :title="t(tool.nameKey)"
        @click="selectTool(tool.id)"
      >
        <svg viewBox="0 0 24 24" class="rail-icon" v-html="icon(tool.icon)" />
        <span class="rail-label">{{ t(tool.nameKey) }}</span>
      </button>

      <button class="rail-item soon" :title="t('nav.comingSoonHint')" @click="onComingSoon">
        <svg viewBox="0 0 24 24" class="rail-icon" v-html="icon('soon')" />
        <span class="rail-label">{{ t('nav.comingSoon') }}</span>
      </button>

      <div class="rail-spacer" />
      <button class="rail-item" :title="t('nav.about')" @click="aboutOpen = true">
        <svg viewBox="0 0 24 24" class="rail-icon" v-html="icon('info')" />
        <span class="rail-label">{{ t('nav.about') }}</span>
      </button>
    </aside>

    <!-- 主区域 -->
    <div class="main">
      <header class="cmdbar">
        <div class="titles">
          <strong>{{ t(activeTool.nameKey) }}</strong>
          <span class="muted">{{ t(activeTool.descriptionKey) }}</span>
        </div>
        <div class="cmd-actions">
          <StatChip :label="adbChip.label" :state="adbChip.state" :detail="adbChip.detail" />
          <StatChip :label="ocrChip.label" :state="ocrChip.state" :detail="ocrChip.detail" />
          <span class="badge">v{{ state.version }}</span>
          <select class="input lang" :value="locale" @change="changeLanguage">
            <option v-for="lang in languages" :key="lang" :value="lang">
              {{ languageLabels[lang] ?? lang }}
            </option>
          </select>
          <button class="btn ghost" :title="t('nav.theme')" @click="onToggleTheme">
            {{ theme === 'dark' ? '☾' : '☀' }}
          </button>
          <button class="btn ghost" :title="t('nav.settings')" @click="drawer = true">⚙</button>
        </div>
      </header>

      <main class="workspace">
        <component
          :is="activeComponent"
          v-if="activeComponent"
          :key="activeId"
          :tool="activeTool"
        />
        <div v-else class="panel">
          <div class="empty">{{ t('app.noView') }}</div>
        </div>
      </main>
    </div>

    <SettingsDrawer
      v-if="drawer"
      :tool="activeTool"
      @close="drawer = false"
      @saved="refreshEnv"
    />
    <AboutDialog v-if="aboutOpen" :version="state.version" @close="aboutOpen = false" />
    <ToastHost />
  </div>

  <div v-else class="boot">
    <div class="boot-card">
      <div class="boot-title">{{ t('app.name') }}</div>
      <div class="muted">{{ bootError || t('app.loading') }}</div>
    </div>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* 左侧工具轨 */
.rail {
  width: 88px;
  flex: 0 0 88px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  background: var(--surface);
  border-right: 1px solid var(--line);
}

.mark {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  margin-bottom: 10px;
  border-radius: 10px;
  background: var(--brand-soft);
  color: var(--brand);
  font-size: 16px;
}

.rail-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 9px 4px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}

.rail-item:hover {
  background: var(--surface-2);
  color: var(--text);
}

.rail-item.active {
  background: var(--surface-2);
  border-color: var(--line-strong);
  color: var(--brand);
}

/* 「敬请期待」：占位入口，视觉上弱化，点了只给提示 */
.rail-item.soon {
  opacity: 0.55;
  border-style: dashed;
  border-color: var(--line);
}

.rail-item.soon:hover {
  opacity: 1;
  color: var(--brand);
}

.rail-icon {
  width: 22px;
  height: 22px;
}

.rail-label {
  font-size: 10px;
  line-height: 1.25;
  text-align: center;
  max-width: 100%;
  overflow-wrap: break-word;
}

.rail-spacer {
  flex: 1;
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.cmdbar {
  height: 56px;
  flex: 0 0 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 16px;
  border-bottom: 1px solid var(--line);
  background: var(--surface);
}

.titles {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.titles strong {
  font-size: 14px;
}

.titles .muted {
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cmd-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.lang {
  width: 118px;
  height: 30px;
}

.workspace {
  flex: 1;
  min-height: 0;
  min-width: 0;
  padding: 14px;
  overflow: hidden;
}

.boot {
  height: 100vh;
  display: grid;
  place-items: center;
}

.boot-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}

.boot-title {
  font-size: 18px;
  letter-spacing: 0.08em;
  color: var(--brand);
}
</style>
