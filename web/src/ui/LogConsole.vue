<!--
  LogConsole.vue —— 实时日志面板

  读取 useJob() 的 logs；新日志追加时自动滚到底，
  但用户手动往上滚后暂停自动滚动，避免看历史时被拽走。
-->
<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'

import type { JobLog } from '../platform/types'

const props = withDefaults(defineProps<{ logs: JobLog[]; showHead?: boolean }>(), {
  showHead: true,
})

const box = ref<HTMLElement | null>(null)
const pinned = ref(true)

function onScroll() {
  const element = box.value
  if (!element) return
  // 距离底部 24px 内视为“跟随最新”
  pinned.value = element.scrollHeight - element.scrollTop - element.clientHeight < 24
}

watch(
  () => props.logs.length,
  async () => {
    if (!pinned.value) return
    await nextTick()
    const element = box.value
    if (element) element.scrollTop = element.scrollHeight
  },
)

async function copyAll() {
  const text = props.logs.map((item) => `[${item.time}] ${item.text}`).join('\n')
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    // WebView2 里剪贴板可能被拒；这里退化为选中文本
  }
}
</script>

<template>
  <div class="console">
    <div v-if="showHead" class="console-head">
      <span class="muted">运行日志</span>
      <button class="btn ghost sm" @click="copyAll">复制</button>
    </div>
    <div ref="box" class="console-body" @scroll="onScroll">
      <div v-if="!logs.length" class="muted empty-line">暂无日志</div>
      <div v-for="item in logs" :key="item.seq" class="line" :class="item.level">
        <span class="time mono">{{ item.time }}</span>
        <span class="text">{{ item.text }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.console {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.console-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid var(--line);
  font-size: 11px;
}

.console-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 8px 10px;
  font-family: var(--font-mono);
  font-size: 11.5px;
  line-height: 1.7;
}

.empty-line {
  padding: 8px 0;
}

.line {
  display: flex;
  gap: 8px;
  white-space: pre-wrap;
  word-break: break-all;
}

.time {
  flex: 0 0 auto;
  color: var(--muted);
}

.line.warn .text {
  color: var(--warn);
}

.line.error .text {
  color: var(--danger);
}

.line.success .text {
  color: var(--ok);
}
</style>
