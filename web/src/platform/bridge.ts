/**
 * pywebview 桥接层（bridge.ts）
 *
 * 桌面端把 Python 后端暴露成 window.pywebview.api；本文件负责：
 * - 等待桥就绪（页面可能先于 Python 注入完成而加载）；
 * - 用统一信封调用后端方法，并把失败信封转换成 BridgeError；
 * - 提供 callTool 语法糖，专门调用某个工具的 action。
 *
 * 后端约定：成功 {ok:true,data}；失败 {ok:false,error:{code,message,detail}}。
 */

declare global {
  interface Window {
    pywebview?: {
      api: Record<string, (...args: unknown[]) => Promise<unknown>>
    }
  }
}

// 把后端的错误信封封装成异常，调用方 catch 后可以读取 code / detail
export class BridgeError extends Error {
  code: string
  detail: string

  constructor(code: string, message: string, detail = '') {
    super(message)
    this.code = code
    this.detail = detail
  }
}

// 就绪 Promise 的缓存：多次调用 waitReady 只监听一次事件
let readyPromise: Promise<void> | null = null

// 等待 pywebview 就绪：已注入则立刻返回，否则等 pywebviewready 事件（最多 6 秒）
export function waitReady(): Promise<void> {
  if (window.pywebview?.api) return Promise.resolve()
  if (readyPromise) return readyPromise

  readyPromise = new Promise<void>((resolve, reject) => {
    const timer = window.setTimeout(
      () => reject(new BridgeError('BRIDGE_TIMEOUT', '无法连接到后端，请从桌面程序启动')),
      6000,
    )
    window.addEventListener(
      'pywebviewready',
      () => {
        window.clearTimeout(timer)
        resolve()
      },
      { once: true },
    )
  })
  return readyPromise
}

/**
 * 调用后端方法并拆信封。
 * - 自动等待桥就绪；
 * - 后端不存在该方法时抛 NO_METHOD；
 * - 成功返回信封里的 data，失败把 error 转成 BridgeError；
 * - 兼容旧行为：返回值不像信封时原样当作结果返回。
 */
export async function invoke<T = unknown>(method: string, ...args: unknown[]): Promise<T> {
  await waitReady()
  const api = window.pywebview?.api
  const fn = api?.[method]
  if (!fn) throw new BridgeError('NO_METHOD', `后端缺少方法 ${method}`)

  const raw = (await fn(...args)) as
    | { ok: true; data: T }
    | { ok: false; error: { code: string; message: string; detail: string } }

  if (raw && typeof raw === 'object' && 'ok' in raw) {
    if (!raw.ok) throw new BridgeError(raw.error.code, raw.error.message, raw.error.detail)
    return raw.data
  }
  return raw as T
}

/**
 * 调用某个工具的 action。
 * 对应后端 Api.tool_call(tool, action, payload)，最终由 Registry 找到该工具注册的处理器。
 */
export function callTool<T = unknown>(
  tool: string,
  action: string,
  payload: Record<string, unknown> = {},
): Promise<T> {
  return invoke<T>('tool_call', tool, action, payload)
}
