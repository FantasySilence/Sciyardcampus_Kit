import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  // 用相对路径：前端由 pywebview 本地 HTTP 服务托管，不假设部署在域名根目录
  base: './',
  plugins: [vue()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    target: 'chrome110',
    assetsInlineLimit: 4096,
  },
  server: {
    port: 5173,
    strictPort: true,
  },
})
