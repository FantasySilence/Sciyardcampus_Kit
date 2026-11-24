# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 前端与后端的通信门面（pywebview 的 js_api）            #
# ================================================================== #
# 约定：公开方法只做参数兜底 + 包返回信封，真正逻辑在同名 _ 私有方法里，
# 便于单测。所有方法都返回 {ok, data|error}，前端不会看到 traceback。

from __future__ import annotations

import os
from typing import Any

from scikit import __version__, const
from scikit.errors import AppError, envelope
from scikit.paths import version_info
from scikit.platform.registry import Context, Registry
from scikit.platform.storage import Runtime, StorageManager


class Api:
    """pywebview 的 js_api 门面。"""

    def __init__(self, runtime: Runtime, registry: Registry) -> None:
        self._rt = runtime
        self._registry = registry
        # 所有工具动作共用同一个 Context：它负责按工具 id 隔离设置
        self._ctx = Context(runtime, registry)
        self._storage = StorageManager(runtime)

    # ------ 状态 ------ #
    def app_state(self) -> dict:
        """前端首屏：版本、偏好、全部工具清单、存储信息。"""

        return envelope(self._app_state)

    def _app_state(self) -> dict:
        prefs = self._prefs()
        info = version_info()
        return {
            "version": info.get("version", __version__),
            "name": info.get("name", "数苑校园工具包"),
            "language": prefs["language"],
            "theme": prefs["theme"],
            "lastTool": prefs["lastTool"],
            "tools": self._registry.manifests(),
            "storage": self._storage.info(),
            # 开发模式下前端跑在 Vite 端口，媒体要拼绝对地址
            "mediaBase": self._rt.media_base,
        }

    def app_set_pref(self, key: str, value: Any) -> dict:
        """设置一条应用偏好（语言 / 主题 / 上次打开的工具）。"""

        return envelope(self._set_pref, key, value)

    def _set_pref(self, key: str, value: Any) -> dict:
        allowed = {"language", "theme", "lastTool"}
        if key not in allowed:
            raise AppError("INVALID_PREF", f"未知偏好：{key}")
        prefs = self._prefs()
        prefs[key] = value
        self._rt.store.save("app", prefs)
        return prefs

    def app_save_window(self, width: int, height: int) -> dict:
        """记录窗口尺寸，下次启动时恢复。"""

        def run() -> dict:
            prefs = self._prefs()
            prefs["window"] = {"width": int(width), "height": int(height)}
            self._rt.store.save("app", prefs)
            return prefs

        return envelope(run)

    # ------ 工具 ------ #
    def tool_manifests(self) -> dict:
        """返回所有工具描述（侧栏据此渲染，前端不硬编码工具列表）。"""

        return envelope(self._registry.manifests)

    def tool_call(self, tool: str, action: str, payload: dict | None = None) -> dict:
        """调用某工具的动作；payload 允许为 None。"""

        return envelope(self._call, tool, action, payload or {})

    def _call(self, tool: str, action: str, payload: dict) -> dict:
        # 动作若返回 jobId，说明是长任务；否则就是同步结果
        return self._registry.call(tool, action, payload, self._ctx)

    # ------ 设置 ------ #
    def settings_get(self, tool: str) -> dict:
        """读取某工具设置（逐字段清洗过）。"""

        return envelope(self._ctx.settings, tool)

    def settings_save(self, tool: str, values: dict) -> dict:
        """保存某工具设置。"""

        return envelope(self._ctx.save_settings, tool, values or {})

    def settings_reset(self, tool: str) -> dict:
        """恢复 schema 里的默认值。"""

        def run() -> dict:
            defaults = self._registry.get(tool).manifest.schema.defaults()
            return self._ctx.save_settings(tool, defaults)

        return envelope(run)

    # ------ 任务 ------ #
    def job_status(self, job_id: str, since: int = 0) -> dict:
        """查询任务状态；since 用来拿增量日志。"""

        return envelope(self._rt.jobs.status, job_id, int(since or 0))

    def job_cancel(self, job_id: str) -> dict:
        """请求取消任务。"""

        return envelope(self._rt.jobs.cancel, job_id)

    def job_active(self) -> dict:
        """当前是否有任务在跑。"""

        return envelope(self._rt.jobs.active)

    # ------ 环境 ------ #
    def env_check(self) -> dict:
        """自检 adb / Tesseract / 数据目录。"""

        def run() -> dict:
            settings = self._ctx.settings("export")
            return self._rt.env.check(settings)

        return envelope(run)

    def device_connect(self, address: str = "") -> dict:
        """执行 adb connect 并返回设备列表。"""

        def run() -> dict:
            settings = self._ctx.settings("export")
            return self._rt.env.connect(address, settings)

        return envelope(run)

    # ------ 数据目录 ------ #
    def storage_info(self) -> dict:
        """查询当前数据目录。"""

        return envelope(self._storage.info)

    def storage_pick_dir(self) -> dict:
        """弹目录选择框；取消时返回 {cancelled: True}。"""

        def run() -> dict:
            path = self._storage.pick_dir()
            return {"cancelled": True} if not path else {"path": path}

        return envelope(run)

    def storage_set_dir(self, path: str) -> dict:
        """切换数据目录。"""

        return envelope(self._storage.set_dir, path)

    def storage_reset(self) -> dict:
        """恢复默认数据目录。"""

        return envelope(self._storage.reset)

    def storage_open_dir(self) -> dict:
        """在资源管理器打开数据目录。"""

        return envelope(self._storage.open_dir)

    # ------ 系统 ------ #
    def file_pick(self, kind: str = "file") -> dict:
        """弹文件/目录选择框；设置抽屉的 path 字段用。"""

        def run() -> dict:
            import webview

            window = self._rt.window
            if window is None:
                raise AppError("NO_WINDOW", "窗口尚未就绪")
            if kind == "dir":
                result = window.create_file_dialog(webview.FileDialog.FOLDER)
            else:
                result = window.create_file_dialog(
                    webview.FileDialog.OPEN,
                    file_types=("可执行文件 (*.exe)", "所有文件 (*.*)"),
                )
            if not result:
                return {"cancelled": True}
            return {"path": str(result[0] if isinstance(result, (list, tuple)) else result)}

        return envelope(run)

    def open_path(self, relative: str) -> dict:
        """用系统默认程序打开数据目录内的文件 / 文件夹。"""

        def run() -> None:
            target = self._rt.paths.resolve_rel(relative)
            if not target.exists():
                raise AppError("NOT_FOUND", "文件不存在", relative)
            os.startfile(str(target))  # noqa: S606 - Windows 桌面应用

        return envelope(run)

    def open_external(self, url: str) -> dict:
        """用默认浏览器打开 http(s) 链接。"""

        def run() -> None:
            if not url.startswith(("http://", "https://")):
                raise AppError("INVALID_URL", "只允许打开 http(s) 链接")
            import webbrowser

            webbrowser.open(url)

        return envelope(run)

    def clipboard_write(self, text: str) -> dict:
        """写系统剪贴板（WebView2 里 navigator.clipboard 不稳定）。"""

        return envelope(_clipboard_write, text)

    # ------ 内部 ------ #
    def _prefs(self) -> dict:
        """读取应用偏好：只保留认识的键，缺的用默认值补齐。"""

        defaults = const.APP_PREFS_DEFAULT
        saved = self._rt.store.load("app", defaults)
        prefs = dict(defaults)
        prefs.update({key: saved[key] for key in defaults if key in saved})
        return prefs


def _clipboard_write(text: str) -> bool:
    """Windows 剪贴板写入（CF_UNICODETEXT）。"""

    import ctypes
    from ctypes import wintypes

    cf_unicode = const.CLIPBOARD_CF_UNICODETEXT
    gmem_moveable = const.CLIPBOARD_GMEM_MOVEABLE

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL

    data = str(text).encode("utf-16-le") + b"\x00\x00"
    handle = kernel32.GlobalAlloc(gmem_moveable, len(data))
    if not handle:
        raise AppError("CLIPBOARD_FAILED", "剪贴板分配失败")
    pointer = kernel32.GlobalLock(handle)
    try:
        ctypes.memmove(pointer, data, len(data))
    finally:
        kernel32.GlobalUnlock(handle)

    if not user32.OpenClipboard(None):
        raise AppError("CLIPBOARD_FAILED", "剪贴板被其他程序占用")
    try:
        user32.EmptyClipboard()
        user32.SetClipboardData(cf_unicode, handle)
    finally:
        user32.CloseClipboard()
    return True
