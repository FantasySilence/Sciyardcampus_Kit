# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 工具注册表：manifest、动作派发、执行上下文              #
# ================================================================== #
# 上层 api.py 不认识任何具体工具，只在这里按 id 查表并派发动作。

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from scikit.errors import AppError
from scikit.platform.schema import SettingsSchema, get_path, set_path

# 动作处理函数签名：(payload, Context) -> 可 JSON 序列化的 dict
Handler = Callable[[dict, "Context"], dict]


@dataclass
class ToolManifest:
    """一个工具的静态描述：身份信息 + 设置 schema + 动作清单 + 结果列。"""

    id: str
    name_key: str
    icon: str
    order: int
    version: str
    schema: SettingsSchema
    actions: list[dict] = field(default_factory=list)
    columns: list[dict] = field(default_factory=list)
    description_key: str = ""

    def to_dict(self) -> dict:
        """转成前端消费的结构：键名统一 camelCase。"""

        return {
            "id": self.id,
            "nameKey": self.name_key,
            "descriptionKey": self.description_key,
            "icon": self.icon,
            "order": self.order,
            "version": self.version,
            "actions": self.actions,
            "columns": self.columns,
            "settingsSchema": self.schema.to_dict(),
        }


@dataclass
class RegisteredTool:
    """注册表里真正保存的一条记录：描述 + 动作处理函数表。"""

    manifest: ToolManifest
    handlers: dict[str, Handler]
    legacy: Callable[[dict], dict] | None = None


class Context:
    """动作执行上下文：给工具提供设置、路径、任务、会话、环境。"""

    def __init__(self, runtime: Any, registry: Registry) -> None:
        self._runtime = runtime
        self._registry = registry

    # ------ 运行时服务 ------ #
    @property
    def runtime(self) -> Any:
        """运行期共享状态（窗口、数据目录等）。"""

        return self._runtime

    @property
    def jobs(self) -> Any:
        """任务管理器：工具动作通过它启动后台任务。"""

        return self._runtime.jobs

    @property
    def paths(self) -> Any:
        """产物路径解析器。"""

        return self._runtime.paths

    @property
    def sessions(self) -> Any:
        """检查会话仓储。"""

        return self._runtime.sessions

    @property
    def env(self) -> Any:
        """设备 / OCR / 数据目录自检。"""

        return self._runtime.env

    # ------ 设置 ------ #
    def settings(self, tool_id: str) -> dict:
        """读取某工具设置并逐字段清洗，返回嵌套 dict。"""

        tool = self._registry.get(tool_id)
        schema = tool.manifest.schema
        raw = self._runtime.store.load(tool_id, schema.defaults())
        data: dict = {}
        for item in schema.fields:
            try:
                value = item.coerce(get_path(raw, item.key, item.default))
            except AppError:
                # 单个字段坏掉只影响它自己，界面仍能正常打开
                value = item.default
            set_path(data, item.key, value)
        return data

    def save_settings(self, tool_id: str, values: dict) -> dict:
        """校验并保存某工具设置，返回清洗后的结果。"""

        tool = self._registry.get(tool_id)
        validated = tool.manifest.schema.validate(values)
        self._runtime.store.save(tool_id, validated)
        return validated

    # ------ 工具自有 JSON 文档 ------ #
    def doc_load(self, tool_id: str, name: str, default: dict | None = None) -> dict:
        """读取工具自有的 JSON 文档（与设置分文件）。"""

        self._registry.get(tool_id)
        data = self._runtime.store.load(f"{tool_id}_{name}", default or {})
        return data if isinstance(data, dict) else dict(default or {})

    def doc_save(self, tool_id: str, name: str, data: dict) -> dict:
        """写入工具自有的 JSON 文档。"""

        self._registry.get(tool_id)
        if not isinstance(data, dict):
            raise AppError("INVALID_DATA", "文档内容必须是对象")
        return self._runtime.store.save(f"{tool_id}_{name}", data)


class Registry:
    """工具注册表：注册、查找、枚举与派发动作。"""

    def __init__(self) -> None:
        """初始化空注册表，键是工具 id。"""

        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        manifest: ToolManifest,
        handlers: dict[str, Handler],
        legacy: Callable[[dict], dict] | None = None,
    ) -> None:
        """注册一个工具；id 重复说明代码写错了，直接抛 ValueError。"""

        if manifest.id in self._tools:
            raise ValueError(f"tool already registered: {manifest.id}")
        self._tools[manifest.id] = RegisteredTool(manifest, handlers, legacy)

    def get(self, tool_id: str) -> RegisteredTool:
        """按 id 取已注册工具；不存在时抛 AppError。"""

        tool = self._tools.get(tool_id)
        if tool is None:
            raise AppError("UNKNOWN_TOOL", f"未知工具：{tool_id}")
        return tool

    def ids(self) -> list[str]:
        """按 manifest.order 升序返回工具 id。"""

        return sorted(self._tools, key=lambda item: self._tools[item].manifest.order)

    def manifests(self) -> list[dict]:
        """返回所有工具描述，顺序与 ids() 一致。"""

        return [self._tools[item].manifest.to_dict() for item in self.ids()]

    def manifest(self, tool_id: str) -> dict:
        """返回单个工具描述。"""

        return self.get(tool_id).manifest.to_dict()

    def call(self, tool_id: str, action: str, payload: dict, ctx: Context) -> dict:
        """按 id + 动作名派发；未知工具/动作都转成 AppError。"""

        tool = self.get(tool_id)
        handler = tool.handlers.get(action)
        if handler is None:
            raise AppError("UNKNOWN_ACTION", f"工具 {tool_id} 没有动作 {action}")
        return handler(payload, ctx)
