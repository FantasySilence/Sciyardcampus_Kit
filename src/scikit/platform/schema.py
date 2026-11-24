# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 设置字段描述符：默认值、类型转换、范围校验、表单生成    #
# ================================================================== #
# 字段用点号路径（如 card.safeTop）描述嵌套结构，前端据此自动生成设置界面。

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any

from scikit.errors import AppError


# ------ 点号路径读写 ------ #
def get_path(data: dict, dotted: str, default: Any = None) -> Any:
    """按 "a.b.c" 取值；中间任一层缺失或不是对象时返回 default。"""

    node: Any = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def has_path(data: dict, dotted: str) -> bool:
    """判断点号路径是否真实存在（即使值为 None 也算存在）。"""

    node: Any = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def set_path(data: dict, dotted: str, value: Any) -> None:
    """按点号路径写入；中间层不存在时自动建空字典。"""

    parts = dotted.split(".")
    node = data
    for part in parts[:-1]:
        nxt = node.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            node[part] = nxt
        node = nxt
    node[parts[-1]] = value


@dataclass
class Field:
    """一个设置字段的完整描述：前端生成控件，后端做类型转换与范围校验。"""

    key: str  # 支持点号路径，如 card.safeTop
    label: str  # i18n key
    type: str = "float"  # int | float | bool | enum | string | path
    default: Any = 0
    # min / max 是闭区间；step 是输入框步长；digits 是展示小数位
    min: float | None = None
    max: float | None = None
    step: float | None = None
    digits: int = 4
    unit: str = ""
    # 仅 type=enum 时使用：每项形如 {"value": 实际值, "label": i18n key}
    options: list[dict] | None = None
    hint: str = ""
    # 仅 type=path 时使用：dir 选目录，file 选文件
    pick: str = "dir"

    def to_dict(self) -> dict:
        """转成前端可直接消费的 JSON。"""

        return {
            "key": self.key,
            "label": self.label,
            "type": self.type,
            "default": self.default,
            "min": self.min,
            "max": self.max,
            "step": self.step,
            "digits": self.digits,
            "unit": self.unit,
            "options": self.options,
            "hint": self.hint,
            "pick": self.pick,
        }

    def coerce(self, value: Any) -> Any:
        """把外部值转成本字段声明的类型，并检查 min / max。"""

        try:
            if self.type == "bool":
                if isinstance(value, str):
                    return value.strip().lower() in ("1", "true", "yes", "on")
                return bool(value)
            if self.type == "enum":
                allowed = [opt["value"] for opt in (self.options or [])]
                if value not in allowed:
                    text = str(value).strip()
                    if text in allowed:
                        return text
                    raise ValueError(value)
                return value
            if self.type in ("string", "path"):
                return str(value)
            number = float(value)
            if self.type == "int":
                if abs(number - round(number)) > 1e-9:
                    raise ValueError(value)
                number = int(round(number))
        except Exception as error:  # noqa: BLE001
            raise AppError(
                "INVALID_SETTING", f"「{self.label}」取值无效", str(error)
            ) from error

        if self.min is not None and number < self.min:
            raise AppError(
                "INVALID_SETTING", f"「{self.label}」不能小于 {self.min}", str(number)
            )
        if self.max is not None and number > self.max:
            raise AppError(
                "INVALID_SETTING", f"「{self.label}」不能大于 {self.max}", str(number)
            )
        return number


@dataclass
class Group:
    """设置界面里的一个分组（渲染成一个折叠面板）。"""

    id: str
    label: str
    fields: list[Field] = dc_field(default_factory=list)

    def to_dict(self) -> dict:
        """转成前端结构：分组 id / i18n 标题 / 字段列表。"""

        return {
            "id": self.id,
            "label": self.label,
            "fields": [f.to_dict() for f in self.fields],
        }


@dataclass
class SettingsSchema:
    """一个工具的全部设置：版本号 + 若干分组。"""

    version: int
    groups: list[Group]

    @property
    def fields(self) -> list[Field]:
        """把所有分组的字段摊平，顺序就是界面显示顺序。"""

        return [f for group in self.groups for f in group.fields]

    def defaults(self) -> dict:
        """生成一份全部取默认值的设置字典（按点号路径展开）。"""

        data: dict = {}
        for field in self.fields:
            set_path(data, field.key, field.default)
        return data

    def validate(self, raw: dict | None) -> dict:
        """把任意来源的原始设置清洗成合法字典：缺项补默认值，坏值抛错。"""

        raw = raw if isinstance(raw, dict) else {}
        data: dict = {}
        for field in self.fields:
            value = get_path(raw, field.key, field.default)
            set_path(data, field.key, field.coerce(value))
        return data

    def to_dict(self) -> dict:
        """导出给前端的完整 schema。"""

        return {
            "version": self.version,
            "groups": [group.to_dict() for group in self.groups],
        }
