# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 运行期路径解析：资源、前端产物、配置、文档目录          #
# ================================================================== #
# 本文件职责：回答“资源在哪、数据默认写哪”这类路径问题。
# 源码运行与 PyInstaller 打包后的目录结构不同，全部差异收敛在这里。

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from scikit import const


def is_frozen() -> bool:
    """是否运行在 PyInstaller 打包出的 exe 中（打包后 sys.frozen 为 True）。"""

    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """可执行文件所在目录；开发模式下是仓库根目录。"""

    if is_frozen():
        return Path(sys.executable).resolve().parent
    # 本文件是 <仓库>/src/scikit/paths.py，往上两级即仓库根目录
    return Path(__file__).resolve().parents[2]


def _bundle_dir() -> Path:
    """只读资源（web/dist、resources）的根目录；打包后是临时解包目录。"""

    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", app_dir()))
    return app_dir()


def resource_dir() -> Path:
    """图标、版本号等只读资源所在目录。"""

    return _bundle_dir() / const.RESOURCES_DIR_NAME


def web_dir() -> Path:
    """前端构建产物目录（npm run build 的输出）。"""

    return _bundle_dir() / const.WEB_DIR_NAME / const.WEB_DIST_DIR_NAME


def appdata_dir() -> Path:
    """用户级配置目录：%APPDATA%/Sciyardcampus_Kit，其它平台退回 ~/.sciyardcampus_kit。"""

    base = os.environ.get(const.APPDATA_ENV_VAR)
    if base:
        return Path(base) / const.APP_DIR_NAME
    return Path.home() / const.APPDATA_FALLBACK_DIR_NAME


def icon_path() -> Path:
    """窗口与任务栏图标（.ico）；文件不存在时调用方跳过设置图标。"""

    return (
        resource_dir() / const.RESOURCE_ICON_SUBDIR / const.ICON_FILENAME
    )


def version_info() -> dict:
    """读取 resources/version.json；读不到就退回代码内常量。"""

    path = resource_dir() / const.VERSION_FILENAME
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
    except Exception:  # noqa: BLE001 - 资源缺失不应阻止启动
        pass
    # 延迟导入避免 paths 被 __init__ 早期引用时形成循环
    from scikit import __version__

    return {"version": __version__, "name": const.APP_NAME}
