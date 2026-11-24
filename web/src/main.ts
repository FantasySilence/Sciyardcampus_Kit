/**
 * 前端入口（main.ts）
 *
 * 职责：挂载 Vue 应用、加载全局样式。
 * 主题与语言由 App.vue 在拿到后端 app_state 后应用。
 */

import { createApp } from 'vue'

import App from './App.vue'
import './styles/base.css'

createApp(App).mount('#app')
