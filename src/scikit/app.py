# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 应用启动：数据目录、静态服务、媒体路由、WebView 窗口    #
# ================================================================== #
# 前端用本地 HTTP 托管（而不是 file://），这样 fetch、相对路径、
# 缩略图接口都能正常工作。服务只绑 127.0.0.1，随机端口。

from __future__ import annotations

import argparse
import hashlib
import mimetypes
import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from scikit import const
from scikit.api import Api
from scikit.env import Environment
from scikit.errors import AppError
from scikit.jobs import JobManager
from scikit.paths import icon_path, web_dir
from scikit.pipeline.artifact_paths import ArtifactPaths
from scikit.platform import locator
from scikit.platform.storage import Runtime
from scikit.platform.store import Store
from scikit.session import SessionStore
from scikit.tools import build_registry


def _fatal(message: str, detail: str = "") -> None:
    """启动阶段的致命错误：弹系统消息框；弹不出来就写 stderr。"""

    text = message if not detail else f"{message}\n\n{detail}"
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None, text, const.APP_NAME_CN, const.MB_ICONERROR
        )
    except Exception:  # noqa: BLE001
        print(text, file=sys.stderr)


def _thumbnail(source: Path, thumbs_dir: Path, width: int) -> Path:
    """
    生成/复用缩略图。

    缓存键包含源文件 mtime，源图被覆盖后会自动换新文件。
    """

    try:
        mtime = int(source.stat().st_mtime)
    except OSError as error:
        raise AppError("NOT_FOUND", "图片不存在", str(source)) from error
    key = hashlib.sha1(f"{source}|{mtime}|{width}".encode()).hexdigest()
    target = thumbs_dir / f"{key}{const.PNG_SUFFIX}"
    if target.exists():
        return target

    from PIL import Image

    thumbs_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail((width, const.MEDIA_MAX_SOURCE_HEIGHT))
        image.save(target, format="PNG")
    return target


def _make_handler(dist: Path, runtime: Runtime):
    """生成静态文件 + /media 的请求处理器类。"""

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dist), **kwargs)

        def end_headers(self) -> None:
            # 统一禁缓存：刷新后一定拿到最新前端/图片
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            super().end_headers()

        def do_OPTIONS(self) -> None:  # noqa: N802 - 覆盖基类方法
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802 - 覆盖基类方法
            parsed = urlparse(self.path)
            if parsed.path == const.MEDIA_ROUTE:
                self._serve_media(parsed)
                return
            super().do_GET()

        def _serve_media(self, parsed) -> None:
            """按 ?path=相对路径&w=宽度 返回原图或缩略图。"""

            query = parse_qs(parsed.query)
            relative = (query.get("path") or [""])[0]
            try:
                width = int((query.get("w") or ["0"])[0] or 0)
            except ValueError:
                width = 0
            try:
                source = runtime.paths.resolve_rel(relative)
                if not source.is_file():
                    raise AppError("NOT_FOUND", "图片不存在", relative)
                if source.suffix.lower() not in const.IMAGE_SUFFIXES:
                    raise AppError("INVALID_PATH", "不是图片", relative)
                if width > 0:
                    width = max(
                        const.MEDIA_MIN_THUMB, min(const.MEDIA_MAX_THUMB, width)
                    )
                    target = _thumbnail(source, runtime.paths.thumbs_dir, width)
                else:
                    target = source
                data = target.read_bytes()
            except AppError as error:
                self.send_error(404, error.message)
                return
            except OSError as error:
                self.send_error(500, str(error))
                return

            content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, fmt: str, *args) -> None:
            # 静默：避免每个缩略图请求都刷控制台
            return

    return Handler


def _start_server(dist: Path, runtime: Runtime) -> str:
    """在后台线程启动本地 HTTP 服务，返回根地址（不带路径）。"""

    handler = _make_handler(dist, runtime)
    server = ThreadingHTTPServer((const.HTTP_HOST, const.HTTP_PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    runtime.media_base = f"http://{const.HTTP_HOST}:{server.server_address[1]}"
    return runtime.media_base


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(prog="SciyardcampusKit")
    parser.add_argument("--dev", action="store_true", help="使用 Vite 开发服务器")
    parser.add_argument(
        "--dev-url",
        default=os.environ.get(const.DEV_URL_ENV_VAR, const.DEFAULT_DEV_URL),
    )
    parser.add_argument("--debug", action="store_true", help="打开 WebView 开发者工具")
    parser.add_argument("--data-dir", default=None, help="自定义数据目录")
    return parser.parse_args(argv)


def _build_runtime(location) -> Runtime:
    """按数据目录装配运行期对象。"""

    paths = ArtifactPaths(location.path)
    paths.ensure()
    jobs = JobManager()
    sessions = SessionStore(paths.sessions_dir)
    store = Store(location.path / ".scikit")
    runtime = Runtime(
        location=location,
        store=store,
        paths=paths,
        jobs=jobs,
        sessions=sessions,
        env=None,
        # WebView2 缓存也放数据根下，保证“所有生成文件都在同一目录”
        webview_dir=paths.webview_dir,
    )
    runtime.env = Environment(runtime)
    return runtime


def run(argv: list[str] | None = None) -> None:
    """应用主流程：解析参数 → 装配 → 开窗口 → 进入 WebView 事件循环。"""

    import webview

    args = _parse_args(argv)
    try:
        location = locator.resolve(args.data_dir)
    except AppError as error:
        _fatal(error.message, error.detail)
        return

    runtime = _build_runtime(location)
    registry = build_registry()
    api = Api(runtime, registry)

    if args.dev:
        url = args.dev_url
    else:
        dist = web_dir()
        if not (dist / const.WEB_INDEX_FILENAME).exists():
            _fatal(
                "前端资源缺失",
                f"未找到 {dist / const.WEB_INDEX_FILENAME}\n"
                "请先在 web/ 目录执行 npm run build。",
            )
            return
        url = _start_server(dist, runtime) + f"/{const.WEB_INDEX_FILENAME}"

    # 开发模式也启动本地服务：媒体/缩略图接口要用
    if args.dev:
        _start_server(web_dir(), runtime)

    prefs = runtime.store.load("app", {})
    window_cfg = prefs.get("window") or {}
    state = {
        "width": int(window_cfg.get("width") or const.WINDOW_DEFAULT_WIDTH),
        "height": int(window_cfg.get("height") or const.WINDOW_DEFAULT_HEIGHT),
        "maximized": bool(window_cfg.get("maximized")),
    }

    window = webview.create_window(
        const.APP_NAME_CN,
        url=url,
        js_api=api,
        width=state["width"],
        height=state["height"],
        maximized=state["maximized"],
        min_size=(const.WINDOW_MIN_WIDTH, const.WINDOW_MIN_HEIGHT),
        background_color=const.WINDOW_BACKGROUND,
        text_select=True,
    )
    runtime.window = window

    def on_maximized() -> None:
        state["maximized"] = True

    def on_restored() -> None:
        state["maximized"] = False

    def on_resized(new_width: int, new_height: int) -> None:
        if state["maximized"]:
            return
        if new_width and new_height:
            state["width"] = int(new_width)
            state["height"] = int(new_height)

    def remember_window() -> None:
        try:
            current = runtime.store.load("app", {})
            current["window"] = {
                "width": state["width"],
                "height": state["height"],
                "maximized": state["maximized"],
            }
            runtime.store.save("app", current)
        except Exception:  # noqa: BLE001 - 配置写失败不影响退出
            pass

    try:
        window.events.maximized += on_maximized
        window.events.restored += on_restored
        window.events.resized += on_resized
        window.events.closed += remember_window
    except Exception:  # noqa: BLE001 - 个别平台没有这些事件
        pass

    icon = icon_path()
    start_kwargs: dict = {
        "debug": args.debug,
        "private_mode": False,
        "storage_path": str(runtime.webview_dir),
    }
    if icon.exists():
        start_kwargs["icon"] = str(icon)

    try:
        webview.start(**start_kwargs)
    except Exception as error:  # noqa: BLE001
        _fatal(
            "无法启动 WebView",
            "请确认系统已安装 Microsoft Edge WebView2 Runtime。\n"
            f"{type(error).__name__}: {error}",
        )
