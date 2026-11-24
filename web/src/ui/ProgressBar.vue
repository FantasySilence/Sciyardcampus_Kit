<!--
  ProgressBar.vue —— 任务进度条

  total 为空表示总量未知（采集到底才停），显示不确定进度动画；
  有 total 时按 current/total 计算宽度，并显示阶段与计数。
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { JobProgress } from '../platform/types'

const props = defineProps<{
  progress: JobProgress | null
  elapsed?: number
}>()

const percent = computed(() => {
  const value = props.progress
  if (!value || !value.total) return 0
  return Math.max(0, Math.min(100, Math.round((value.current / value.total) * 100)))
})

const indeterminate = computed(() => !props.progress?.total)

const text = computed(() => {
  const value = props.progress
  if (!value) return ''
  if (!value.total) return `${value.current} 题`
  return `${value.current} / ${value.total}`
})
</script>

<template>
  <div class="progress">
    <div class="progress-head">
      <span class="label">{{ progress?.label || '' }}</span>
      <span class="muted mono">{{ text }}</span>
    </div>
    <div class="track" :class="{ indeterminate }">
      <div class="bar" :style="indeterminate ? {} : { width: `${percent}%` }" />
    </div>
  </div>
</template>

<style scoped>
.progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.progress-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
}

.label {
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track {
  height: 6px;
  border-radius: 999px;
  background: var(--surface-3);
  overflow: hidden;
}

.bar {
  height: 100%;
  width: 0;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--brand-dim), var(--brand));
  transition: width 0.3s ease;
}

/* 总量未知：一条来回移动的亮条 */
.track.indeterminate .bar {
  width: 32%;
  animation: slide 1.2s ease-in-out infinite;
}

@keyframes slide {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(320%);
  }
}
</style>
