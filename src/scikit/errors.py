# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 统一错误类型与前后端返回信封                            #
# ================================================================== #
# 本文件职责：定义全项目唯一的“可预期错误”异常 AppError，以及前后端约定的
# 返回信封。所有对外 API 都从这里取信封：
#   成功 {ok: True, data}；失败 {ok: False, error: {code, message, detail}}
# 任务线程里的错误也会被转换成同样的结构，前端不需要区分同步/异步来源。

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """可预期错误：带稳定错误码，前端据此展示文案。"""

    def __init__(self, code: str, message: str, detail: str = "") -> None:
        """
        code: 稳定错误码（如 TESSERACT_MISSING），前端可据此分支
        message: 给用户看的中文说明
        detail: 可选排查细节，通常放在提示的第二行
        """

        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail

    def to_dict(self) -> dict:
        """转成前端消费的错误对象。"""

        return {"code": self.code, "message": self.message, "detail": self.detail}


def ok(data: Any = None) -> dict:
    """构造成功信封；data 必须可被 JSON 序列化。"""

    return {"ok": True, "data": data}


def fail(error: AppError) -> dict:
    """把 AppError 转成失败信封。"""

    return {"ok": False, "error": error.to_dict()}


def envelope(fn, *args, **kwargs) -> dict:
    """
    执行并包成信封：AppError 原样透出，其它异常统一降级成 INTERNAL。

    这样 pywebview 的 JS 调用永远不会收到 Python traceback，
    前端只需要处理 {ok:false,error} 这一种失败形态。
    """

    try:
        return ok(fn(*args, **kwargs))
    except AppError as error:
        return fail(error)
    except Exception as error:  # noqa: BLE001 - 最外层兜底
        return fail(AppError("INTERNAL", "内部错误", f"{type(error).__name__}: {error}"))
