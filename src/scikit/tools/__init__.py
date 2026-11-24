# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 工具注册入口：新增工具时只在这里加一行                 #
# ================================================================== #

from __future__ import annotations

from scikit.platform.registry import Registry

from . import export, publish


def build_registry() -> Registry:
    """创建并注册全部工具；顺序由各 manifest 的 order 决定。"""

    registry = Registry()
    registry.register(export.MANIFEST, export.HANDLERS, export.LEGACY)
    registry.register(publish.MANIFEST, publish.HANDLERS, publish.LEGACY)
    return registry
