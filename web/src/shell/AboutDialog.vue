<!--
  AboutDialog.vue —— 关于弹窗

  展示应用名称、版本、简介与技术栈；提供 GitHub 仓库与关闭按钮。
-->
<script setup lang="ts">
import { invoke } from '../platform/bridge'
import { t } from '../platform/i18n'
import { notifyError } from '../platform/toast'

defineProps<{ version: string }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const REPO_URL = 'https://github.com/FantasySilence/Sciyardcampus_Kit'

async function openRepo() {
  try {
    await invoke('open_external', REPO_URL)
  } catch (error) {
    notifyError(error)
  }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <section class="about">
      <div class="mark">◆</div>
      <h2>{{ t('app.name') }}</h2>
      <div class="version mono">v{{ version }}</div>

      <p class="intro">{{ t('about.intro') }}</p>
      <ul class="facts">
        <li>{{ t('about.tech') }}</li>
        <li>{{ t('about.data') }}</li>
        <li>{{ t('about.license') }}</li>
      </ul>

      <div class="actions">
        <button class="btn" @click="openRepo">{{ t('about.repo') }}</button>
        <button class="btn primary" @click="emit('close')">{{ t('action.close') }}</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  background: var(--scrim);
  backdrop-filter: blur(2px);
}

.about {
  width: 460px;
  max-width: 92vw;
  padding: 24px;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow);
}

.mark {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  margin-bottom: 12px;
  border-radius: 12px;
  background: var(--brand-soft);
  color: var(--brand);
  font-size: 20px;
}

h2 {
  margin: 0 0 4px;
  font-size: 18px;
}

.version {
  margin-bottom: 14px;
  color: var(--muted);
  font-size: 12px;
}

.intro {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.7;
}

.facts {
  margin: 0 0 20px;
  padding-left: 18px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.9;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}
</style>
