<!--
  View.vue（作业发布，占位）

  本期只提供占位页：不写假数据、不弹假成功。
  后端 publish.check 明确返回 available=false，后续接真实接口时
  只需要补充 actions.py 与这个页面。
-->
<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { callTool } from '../../platform/bridge'
import { t } from '../../platform/i18n'
import { notifyError } from '../../platform/toast'
import type { ToolDef } from '../../platform/types'

defineProps<{ tool: ToolDef }>()

const planned = ref<string[]>([])
const message = ref('')

onMounted(async () => {
  try {
    const data = await callTool<{
      available: boolean
      message: string
      planned: string[]
    }>('publish', 'check')
    message.value = data.message
    planned.value = data.planned ?? []
  } catch (error) {
    notifyError(error)
  }
})
</script>

<template>
  <div class="publish">
    <section class="panel">
      <div class="panel-head">
        <span>{{ t('publish.title') }}</span>
        <span class="badge warn">{{ t('publish.wip') }}</span>
      </div>
      <div class="panel-body">
        <div class="mark">◆</div>
        <h2>{{ t('publish.headline') }}</h2>
        <p class="muted">{{ message || t('publish.pageDescription') }}</p>

        <div class="planned">
          <div class="planned-title">{{ t('publish.plannedTitle') }}</div>
          <ul>
            <li v-for="item in planned" :key="item">{{ item }}</li>
          </ul>
        </div>

        <div class="row">
          <button class="btn" disabled>{{ t('publish.pickPaper') }}</button>
          <button class="btn primary" disabled>{{ t('publish.publish') }}</button>
        </div>

        <p class="hint">{{ t('publish.hint') }}</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.publish {
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
