# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 占位工具测试：作业发布 / 测试成绩 / 平时成绩           #
# ================================================================== #
# 三个工具都只提供骨架：check 明确返回 available=false，且不写任何数据。

from __future__ import annotations

import pytest

PLACEHOLDERS = ["publish", "exam_scores", "regular_scores"]


@pytest.mark.parametrize("tool_id", PLACEHOLDERS)
def test_placeholder_is_registered_but_unavailable(api, tool_id: str) -> None:
    result = api.tool_call(tool_id, "check")
    assert result["ok"] is True
    data = result["data"]
    assert data["available"] is False
    assert data["reason"] == "NOT_IMPLEMENTED"
    assert data["message"]
    assert data["planned"]


@pytest.mark.parametrize("tool_id", PLACEHOLDERS)
def test_placeholder_writes_no_data(api, data_root, tool_id: str) -> None:
    before = sorted(data_root.sessions_dir.glob("*.json"))
    api.tool_call(tool_id, "check")
    after = sorted(data_root.sessions_dir.glob("*.json"))
    assert before == after


@pytest.mark.parametrize("tool_id", PLACEHOLDERS)
def test_placeholder_rejects_unknown_action(api, tool_id: str) -> None:
    result = api.tool_call(tool_id, "nope")
    assert result["ok"] is False
    assert result["error"]["code"] == "UNKNOWN_ACTION"
