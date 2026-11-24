# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 作业发布工具（占位）：只提供骨架，不接真实接口          #
# ================================================================== #
# 这一版不写假数据、不弹假成功；check 明确返回 available=false。
# 后续接真实发布接口时，只需要在 actions.py 增加动作、在 View.vue 接表单。

from __future__ import annotations

from scikit import const
from scikit.platform.registry import ToolManifest
from scikit.platform.schema import SettingsSchema

MANIFEST = ToolManifest(
    id="publish",
    name_key="publish.name",
    description_key="publish.description",
    icon="publish",
    order=20,
    version="0.0.0",
    schema=SettingsSchema(version=const.SETTINGS_SCHEMA_VERSION, groups=[]),
    actions=[{"id": "check", "labelKey": "publish.action.check"}],
)


def check_action(payload: dict, ctx) -> dict:
    """明确告诉前端“尚未实现”，避免占位页被误解为可用。"""

    return {
        "available": False,
        "reason": "NOT_IMPLEMENTED",
        "message": "作业发布功能尚未实现",
        "planned": ["选择试卷", "选择班级", "设置截止时间", "发布并查看状态"],
    }


HANDLERS = {"check": check_action}
LEGACY = None
