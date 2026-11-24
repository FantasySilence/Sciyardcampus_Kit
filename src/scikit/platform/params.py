# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 请求参数校验：把前端弱类型 JSON 转成后端强类型值        #
# ================================================================== #
# 任何不合法输入都抛 AppError（INVALID_PAYLOAD / INVALID_INPUT），
# 由上层包成返回信封，前端不会看到 traceback。

from __future__ import annotations

from typing import Any

from scikit.errors import AppError


# ------ 基础类型校验 ------ #
def payload_dict(payload: Any) -> dict:
    """把请求 payload 统一成 dict：None 视为空字典，其它非 dict 类型直接拒绝。"""

    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise AppError("INVALID_PAYLOAD", "请求参数格式错误")
    return payload


def obj(payload: dict, key: str) -> dict:
    """取出一个必填的嵌套对象参数；缺失或类型不是 dict 都拒绝。"""

    value = payload.get(key)
    if not isinstance(value, dict):
        raise AppError("INVALID_PAYLOAD", f"缺少参数：{key}")
    return value


def text(payload: dict, key: str, *, default: str = "", label: str | None = None) -> str:
    """取一个字符串参数；数字/布尔会转成字符串，None 视为缺省值。"""

    value = payload.get(key, default)
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        raise AppError("INVALID_INPUT", f"「{label or key}」格式错误")
    return str(value).strip()


def boolean(payload: dict, key: str, *, default: bool = False) -> bool:
    """取一个布尔参数；兼容前端传来的 1/0、'true'/'false'。"""

    value = payload.get(key, default)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def number(
    payload: dict,
    key: str,
    *,
    default: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    label: str | None = None,
) -> float:
    """取一个数值参数并返回 float；越界抛 INVALID_INPUT。"""

    name = label or key
    if key not in payload or payload[key] is None:
        if default is None:
            raise AppError("INVALID_PAYLOAD", f"缺少参数：{name}")
        value = float(default)
    else:
        try:
            value = float(payload[key])
        except (TypeError, ValueError) as error:
            raise AppError("INVALID_INPUT", f"「{name}」必须是数字") from error
    if minimum is not None and value < minimum:
        raise AppError("INVALID_INPUT", f"「{name}」不能小于 {minimum}")
    if maximum is not None and value > maximum:
        raise AppError("INVALID_INPUT", f"「{name}」不能大于 {maximum}")
    return value


def integer(
    payload: dict,
    key: str,
    *,
    default: int | None = None,
    minimum: int | None = None,
    maximum: int | None = None,
    label: str | None = None,
) -> int:
    """取一个整数参数：先按 number() 校验，再要求没有小数部分。"""

    value = number(
        payload, key, default=default, minimum=minimum, maximum=maximum, label=label
    )
    if abs(value - round(value)) > 1e-9:
        raise AppError("INVALID_INPUT", f"「{label or key}」必须是整数")
    return int(round(value))


def choice(
    payload: dict, key: str, options: tuple[str, ...], *, default: str | None = None
) -> str:
    """取一个枚举参数：值必须落在 options 里。"""

    value = payload.get(key, default)
    if value not in options:
        raise AppError("INVALID_INPUT", f"「{key}」取值必须是 {', '.join(options)} 之一")
    return str(value)
