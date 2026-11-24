<!--
  HistoryPanel.vue —— 历史产物

  列出本应用保存过的检查会话，以及目录里只有文件、没有 session 的旧产物。
  点击一条即进入预览检查（旧产物会由后端合成只读会话）。
-->
<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { callTool, invoke } from '../../platform/bridge'
import { t } from '../../platform/i18n'
import { notifyError } from '../../platform/toast'
import type { HistoryEntry, HistoryPayload } from '../../platform/types'

const emit = defineEmits<{ (e: 'open', entry: HistoryEntry): void }>()

const data = ref<HistoryPayload | null>(null)
const loading = ref(false)

async function refresh() {
  loading.value = true
  try {
    data.value = await callTool<HistoryPayload>('export', 'history')
  } catch (error) {
    notifyError(error)
  } finally {
    loading.value = false
  }
}

async function openDataDir() {
  try {
    await invoke('storage_open_dir')
  } catch (error) {
    notifyError(error)
  }
}

onMounted(refresh)
</script>

<template>
  <div class="history">
    <section class="panel">
      <div class="panel-head">
        <span>{{ t('export.history.title') }}</span>
        <div class="row">
          <button class="btn sm" :disabled="loading" @click="refresh">
            {{ t('action.refresh') }}
          </button>
          <button class="btn sm" @click="openDataDir">{{ t('export.action.openData') }}</button>
        </div>
      </div>

      <div class="panel-body">
        <div v-if="loading" class="empty">{{ t('app.loading') }}</div>
        <div v-else-if="!data?.entries?.length" class="empty">{{ t('export.history.empty') }}</div>

        <div v-else class="entry-list">
          <article
            v-for="entry in data.entries"
            :key="`${entry.source}-${entry.id}-${entry.title}`"
            class="entry"
            @click="emit('open', entry)"
          >
            <div class="entry-main">
              <div class="row">
                <strong>{{ entry.title }}</strong>
                <span class="badge">{{ entry.scope.mode === 'paper' ? t('export.history.paper') : t('export.history.type') }}</span>
                <span v-if="entry.source === 'files'" class="badge warn">{{ t('export.history.filesOnly') }}</span>
              </div>
              <div class="hint">
                {{ t('export.history.counts', { total: entry.total, included: entry.included }) }}
                <span v-if="entry.updatedAt"> · {{ entry.updatedAt }}</span>
              </div>
            </div>

            <div class="entry-side">
              <span class="badge" :class="entry.docxExists ? 'brand' : ''">
                {{ entry.docxExists ? t('export.history.docxReady') : t('export.history.noDocx') }}
              </span>
              <span class="open-hint">{{ t('export.history.open') }} →</span>
            </div>
          </article>
        </div>

        <div v-if="data?.inventory" class="inventory">
          <div class="inv-col">
            <div class="inv-title">{{ t('export.history.types') }}</div>
            <div v-if="!data.inventory.types.length" class="hint">{{ t('export.history.none') }}</div>
            <div v-for="item in data.inventory.types" :key="item.name" class="inv-row">
              <span>{{ item.name }}</span>
              <span class="muted mono">
                {{ item.pngs }} / {{ item.txts }}
              </span>
            </div>
          </div>
          <div class="inv-col">
            <div class="inv-title">{{ t('export.history.papers') }}</div>
            <div v-if="!data.inventory.papers.length" class="hint">{{ t('export.history.none') }}</div>
            <div v-for="item in data.inventory.papers" :key="item.name" class="inv-row">
              <span>{{ item.name }}</span>
              <span class="muted mono">{{ item.pngs }} / {{ item.txts }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.history {
  height: 100%;
}

.panel-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.entry-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-2);
  cursor: pointer;
}

.entry:hover {
  border-color: var(--brand-dim);
}

.entry-main {
  min-width: 0;
}

.entry-side {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
}

.open-hint {
  color: var(--brand);
  font-size: 11px;
}

.inventory {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  border-top: 1px solid var(--line);
  padding-top: 14px;
}

.inv-title {
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.inv-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 3px 0;
  font-size: 12px;
}
</style>
