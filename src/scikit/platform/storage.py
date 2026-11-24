# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 运行期共享状态与数据目录管理                            #
# ================================================================== #
# 只处理文件系统层面的事，不理解任何具体工具的配置含义。

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scikit.errors import AppError
from scikit.paths import version_info
from scikit.platform import locator
from scikit.platform.store import Store


@dataclass
class Runtime:
    """运行期共享状态：数据目录、配置仓储、路径、任务、会话、窗口。"""

    location: locator.Location
    store: Store
    paths: Any
    jobs: Any
    sessions: Any
    env: Any
    webview_dir: Path
    media_base: str = ""
    window: object | None = None

    def rebind(self, location: locator.Location) -> None:
        """切换数据目录：换 location，并为新目录重建 Store / 路径 / 会话。"""

        # 延迟导入，避免 storage ↔ pipeline 的循环依赖
        from scikit.pipeline.artifact_paths import ArtifactPaths
        from scikit.session import SessionStore

        self.location = location
        self.store = Store(location.path / ".scikit")
        self.paths = ArtifactPaths(location.path)
        self.paths.ensure()
        self.sessions = SessionStore(self.paths.sessions_dir)


class StorageManager:
    """数据目录操作：查询信息、切换目录、打开目录、清理缓存。"""

    # ------ 可清理的缓存目录 ------ #
    # 只碰这三类「丢了能重算」的目录：缩略图、OCR 临时图、预检截图。
    # sessions / settings / backups 与 resources 里的产物一律不动。
    CACHE_DIRS = ("thumbs_dir", "tmp_dir", "probe_dir")

    def __init__(self, runtime: Runtime) -> None:
        self._rt = runtime

    def info(self) -> dict:
        """返回界面要展示的信息：数据目录、来源、是否可写、版本号。"""

        data = self._rt.location.to_dict()
        data["resources"] = str(self._rt.paths.resources_dir)
        data["version"] = version_info().get("version", "")
        return data

    def cache_info(self) -> dict:
        """统计缓存目录的体积与文件数（供设置页展示）。"""

        entries = []
        total_bytes = 0
        total_files = 0
        for attr in self.CACHE_DIRS:
            folder: Path = getattr(self._rt.paths, attr)
            size, count = _path_size(folder)
            entries.append(
                {
                    "key": attr.removesuffix("_dir"),
                    "path": str(folder),
                    "bytes": size,
                    "files": count,
                }
            )
            total_bytes += size
            total_files += count
        return {"bytes": total_bytes, "files": total_files, "dirs": entries}

    def clear_cache(self) -> dict:
        """清空缓存目录的内容（保留目录本身），返回释放量与跳过数。"""

        if self._rt.jobs.active() is not None:
            raise AppError("JOB_RUNNING", "任务运行中，不能清理缓存")

        freed = 0
        removed = 0
        skipped = 0
        for attr in self.CACHE_DIRS:
            folder: Path = getattr(self._rt.paths, attr)
            folder.mkdir(parents=True, exist_ok=True)
            for entry in list(folder.iterdir()):
                try:
                    freed += _path_size(entry)[0]
                    if entry.is_dir():
                        shutil.rmtree(entry)
                    else:
                        entry.unlink()
                    removed += 1
                except OSError:
                    # 被占用 / 没权限的项跳过，不因为一个文件失败就整体失败
                    skipped += 1
        return {
            "freedBytes": freed,
            "removed": removed,
            "skipped": skipped,
            "cache": self.cache_info(),
        }

    # ------ 切换 ------ #
    def pick_dir(self) -> str | None:
        """弹系统目录选择框；用户取消时返回 None。"""

        import webview

        window = self._rt.window
        if window is None:
            raise AppError("NO_WINDOW", "窗口尚未就绪")
        result = window.create_file_dialog(webview.FileDialog.FOLDER)
        if not result:
            return None
        return str(result[0] if isinstance(result, (list, tuple)) else result)

    def set_dir(self, path: str) -> dict:
        """切换数据目录：校验可写、搬运设置、记住选择，返回新的存储信息。"""

        if not path:
            raise AppError("INVALID_INPUT", "请选择目录")
        if self._rt.jobs.active() is not None:
            raise AppError("JOB_RUNNING", "任务运行中，不能切换数据目录")
        target = Path(path).expanduser()
        if not locator._probe(target):  # noqa: SLF001 - 同包工具函数
            raise AppError("STORAGE_UNWRITABLE", "该目录不可写，请换一个", str(target))
        if target.resolve() == self._rt.location.path.resolve():
            return self.info()

        self._copy_settings(self._rt.store.settings_dir, target / ".scikit" / "settings")
        locator.set_user_location(target)
        if self._rt.location.portable:
            locator.set_portable(target)
        self._rt.rebind(
            locator.Location(path=target, source="user", portable=False, writable=True)
        )
        return self.info()

    def reset(self) -> dict:
        """清除“用户选择的目录”记录，回到默认解析结果。"""

        if self._rt.jobs.active() is not None:
            raise AppError("JOB_RUNNING", "任务运行中，不能重置数据目录")
        locator.clear_user_location()
        location = locator.resolve(None)
        self._rt.rebind(location)
        return self.info()

    def open_dir(self) -> None:
        """在资源管理器里打开当前数据目录（不存在就先创建）。"""

        path = self._rt.location.path
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(path))  # noqa: S606 - Windows 桌面应用

    # ------ 内部 ------ #
    @staticmethod
    def _copy_settings(source: Path, target: Path) -> None:
        """把旧目录的设置复制到新目录；单个文件失败只跳过它。"""

        target.mkdir(parents=True, exist_ok=True)
        if not source.exists():
            return
        for file in source.glob("*.json"):
            try:
                shutil.copy2(file, target / file.name)
            except OSError:
                continue


def _path_size(path: Path) -> tuple[int, int]:
    """统计文件或目录的总字节数与文件数；读不到的项按 0 计。"""

    if not path.exists():
        return 0, 0
    if path.is_file():
        try:
            return path.stat().st_size, 1
        except OSError:
            return 0, 0

    total = 0
    count = 0
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        try:
            total += item.stat().st_size
            count += 1
        except OSError:
            continue
    return total, count
