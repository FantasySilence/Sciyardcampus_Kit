# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 作业发布占位工具测试                                   #
# ================================================================== #

from __future__ import annotations


def test_publish_is_registered_but_unavailable(api) -> None:
    result = api.tool_call("publish", "check")
    assert result["ok"] is True
    data = result["data"]
    assert data["available"] is False
    assert data["reason"] == "NOT_IMPLEMENTED"
    assert data["planned"]


def test_publish_writes_no_data(api, data_root) -> None:
    before = list(data_root.sessions_dir.glob("*.json"))
    api.tool_call("publish", "check")
    after = list(data_root.sessions_dir.glob("*.json"))
    assert before == after
