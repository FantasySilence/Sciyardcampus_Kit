/**
 * 任务轮询（jobs.ts）
 *
 * 后端的采集/OCR/导出都是长任务：tool_call 只返回 jobId，
 * 前端每 500ms 调一次 job_status，拿增量日志与进度。
 *
 * 用法：
 *   const job = useJob()
 *   await job.start('export', 'start_capture', { ... })
 *   watch(() => job.snapshot.value?.status, status => { if (status === 'done') ... })
 *
 * 组件卸载时停止轮询，但后端任务继续跑；重新挂载可以从 history 找回结果。
 */

import { computed, onUnmounted, ref } from 'vue'

import { callTool, invoke } from './bridge'
import type { JobLog, JobSnapshot } from './types'

const POLL_INTERVAL = 500
const MAX_LOGS = 1000

export function useJob() {
  const jobId = ref('')
  const snapshot = ref<JobSnapshot | null>(null)
  const logs = ref<JobLog[]>([])
  const error = ref<unknown>(null)

  let since = 0
  let timer: number | null = null
  let disposed = false

  const running = computed(() => snapshot.value?.status === 'running')
  const terminal = computed(
    () => !!snapshot.value && snapshot.value.status !== 'running',
  )
  const progress = computed(() => snapshot.value?.progress ?? null)

  function stopTimer(): void {
    if (timer !== null) {
      window.clearTimeout(timer)
      timer = null
    }
  }

  /** 拉一次状态；仍在运行就继续排下一次。 */
  async function poll(): Promise<void> {
    if (!jobId.value || disposed) return
    try {
      const data = await invoke<JobSnapshot>('job_status', jobId.value, since)
      snapshot.value = data
      if (data.logs?.length) {
        logs.value.push(...data.logs)
        since = data.logs[data.logs.length - 1].seq
        // 前端只保留最近 1000 条，长任务不撑爆内存
        if (logs.value.length > MAX_LOGS) {
          logs.value.splice(0, logs.value.length - MAX_LOGS)
        }
      }
      if (data.status === 'running') {
        timer = window.setTimeout(poll, POLL_INTERVAL)
      } else {
        stopTimer()
      }
    } catch (cause) {
      error.value = cause
      stopTimer()
    }
  }

  /** 启动一个任务；action 返回 {jobId}。 */
  async function start(
    tool: string,
    action: string,
    payload: Record<string, unknown> = {},
  ): Promise<Record<string, any>> {
    reset()
    const data = await callTool<Record<string, any>>(tool, action, payload)
    jobId.value = String(data.jobId || '')
    if (!jobId.value) throw new Error('后端没有返回 jobId')
    await poll()
    return data
  }

  /** 请求取消；终态由下一次轮询确认。 */
  async function cancel(): Promise<void> {
    if (!jobId.value) return
    await invoke('job_cancel', jobId.value)
  }

  function reset(): void {
    stopTimer()
    jobId.value = ''
    snapshot.value = null
    logs.value = []
    since = 0
    error.value = null
  }

  onUnmounted(() => {
    disposed = true
    stopTimer()
  })

  return { jobId, snapshot, logs, error, running, terminal, progress, start, cancel, reset }
}
