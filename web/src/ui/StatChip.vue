<!--
  StatChip.vue —— 环境状态灯（adb / Tesseract）
-->
<script setup lang="ts">
defineProps<{
  label: string
  state: 'ok' | 'warn' | 'error' | 'muted'
  detail?: string
}>()
</script>

<template>
  <span class="stat" :class="state" :title="detail || label">
    <span class="dot" />
    <span>{{ label }}</span>
  </span>
</template>

<style scoped>
.stat {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 9px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface-2);
  color: var(--muted);
  font-size: 11px;
  white-space: nowrap;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--muted);
}

.stat.ok {
  color: var(--ok);
  border-color: rgba(89, 212, 153, 0.3);
}
.stat.ok .dot {
  background: var(--ok);
}

.stat.warn {
  color: var(--warn);
  border-color: rgba(242, 193, 78, 0.3);
}
.stat.warn .dot {
  background: var(--warn);
}

.stat.error {
  color: var(--danger);
  border-color: rgba(255, 95, 109, 0.3);
}
.stat.error .dot {
  background: var(--danger);
}
</style>
