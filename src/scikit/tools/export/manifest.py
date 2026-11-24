# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 采集导出工具的 manifest 与动作表                       #
# ================================================================== #

from __future__ import annotations

from scikit.platform.registry import ToolManifest

from .actions import (
    history_action,
    probe_action,
    save_text_action,
    session_get_action,
    session_update_action,
    set_render_mode_action,
    start_capture_action,
    start_export_action,
    start_ocr_action,
)
from .schema import SCHEMA

MANIFEST = ToolManifest(
    id="export",
    name_key="export.name",
    description_key="export.description",
    icon="capture",
    order=10,
    version="0.1.0",
    schema=SCHEMA,
    actions=[
        {"id": "probe", "labelKey": "export.action.probe"},
        {"id": "start_capture", "labelKey": "export.action.capture"},
        {"id": "start_ocr", "labelKey": "export.action.ocr"},
        {"id": "start_export", "labelKey": "export.action.export"},
        {"id": "history", "labelKey": "export.action.history"},
    ],
)

HANDLERS = {
    "probe": probe_action,
    "start_capture": start_capture_action,
    "session_get": session_get_action,
    "session_update": session_update_action,
    "save_text": save_text_action,
    "set_render_mode": set_render_mode_action,
    "start_ocr": start_ocr_action,
    "start_export": start_export_action,
    "history": history_action,
}

LEGACY = None
