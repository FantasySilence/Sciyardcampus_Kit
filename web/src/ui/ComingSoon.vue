<!--
  ComingSoon.vue —— 「敬请期待」占位页

  给尚未实现的工具共用：不写假数据、不弹假成功。
  页面内容（说明 + 计划能力）来自后端 tool_call(tool.id, 'check')，
  与作业发布占位保持同一套约定：available=false、reason=NOT_IMPLEMENTED。
-->
<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { callTool } from '../platform/bridge'
import { t } from '../platform/i18n'
import { notifyError } from '../platform/toast'
import type { ToolDef } from '../platform/types'

const props = defineProps<{ tool: ToolDef; prefix: string }>()

const planned = ref<string[]>([])
const message = ref('')

onMounted(async () => {
  try {
    const data = await callTool<{
      available: boolean
      message: string
      planned: string[]
    }>(props.tool.id, 'check')
    message.value = data.message
    planned.value = data.planned ?? []
  } catch (error) {
    notifyError(error)
  }
})
</script>

<template>
  <div class="coming-soon">
    <section class="panel">
      <div class="panel-head">
        <span>{{ t(`${prefix}.title`) }}</span>
        <span class="badge warn">{{ t(`${prefix}.wip`) }}</span>
      </div>
      <div class="panel-body">
        <div class="mark">◆</div>
        <h2>{{ t(`${prefix}.headline`) }}</h2>
        <p class="muted">{{ message || t(`${prefix}.description`) }}</p>

        <div class="planned">
          <div class="planned-title">{{ t(`${prefix}.plannedTitle`) }}</div>
          <ul>
            <li v-for="item in planned" :key="item">{{ item }}</li>
          </ul>
        </div>

        <div class="row">
          <button class="btn" disabled>{{ t(`${prefix}.action.check`) }}</button>
          <button class="btn primary" disabled>{{ t(`${prefix}.action.start`) }}</button>
        </div>

        <p class="hint">{{ t(`${prefix}.hint`) }}</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.coming-soon {
  height: 100%;
  display: grid;
  place-items: stretch;
}

.panel-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 14px;
  max-width: 720px;
  padding: 32px;
}

.mark {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: var(--brand-soft);
  color: var(--brand);
  font-size: 22px;
}

h2 {
  margin: 0;
  font-size: 20px;
}

.planned {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-2);
}

.planned-title {
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.planned ul {
  margin: 8px 0 0;
  padding-left: 18px;
  color: var(--muted);
  line-height: 2;
}
</style>
