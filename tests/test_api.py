# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: API 门面测试：信封、设置、历史、路径校验               #
# ================================================================== #

from __future__ import annotations


def test_app_state_lists_all_tools(api) -> None:
    result = api.app_state()
    assert result["ok"] is True
    data = result["data"]
    assert [tool["id"] for tool in data["tools"]] == [
        "export",
        "publish",
        "exam_scores",
        "regular_scores",
    ]
    # 测试里没有启动 HTTP 服务，mediaBase 允许为空；真实启动时是 127.0.0.1 地址
    assert "mediaBase" in data


def test_settings_roundtrip_and_validation(api) -> None:
    settings = api.settings_get("export")
    assert settings["ok"] is True
    assert settings["data"]["card"]["safeTop"] == 130

    bad = api.settings_save("export", {"card": {"safeTop": 9999}})
    assert bad["ok"] is False
    assert bad["error"]["code"] == "INVALID_SETTING"


def test_unknown_tool_and_action(api) -> None:
    missing_tool = api.tool_call("nope", "run")
    assert missing_tool["ok"] is False
    assert missing_tool["error"]["code"] == "UNKNOWN_TOOL"

    missing_action = api.tool_call("export", "nope")
    assert missing_action["ok"] is False
    assert missing_action["error"]["code"] == "UNKNOWN_ACTION"


def test_history_is_empty_for_fresh_data(api) -> None:
    result = api.tool_call("export", "history")
    assert result["ok"] is True
    assert result["data"]["entries"] == []
    assert result["data"]["inventory"]["types"] == []


def test_session_not_found(api) -> None:
    result = api.tool_call("export", "session_get", {"sessionId": "deadbeef"})
    assert result["ok"] is False
    assert result["error"]["code"] == "SESSION_NOT_FOUND"


def test_open_path_rejects_traversal(api) -> None:
    result = api.open_path("../outside.txt")
    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_PATH"


def test_storage_dir_is_customizable(api, tmp_path, monkeypatch) -> None:
    """设置里换数据根后，resources/.scikit 一起跟过去。"""

    from scikit.paths import app_dir
    from scikit.platform import locator

    # 测试不能真的写用户的 %APPDATA%/location.json
    monkeypatch.setattr(locator, "set_user_location", lambda path: None)

    custom = tmp_path / "custom-data"
    result = api.storage_set_dir(str(custom))
    assert result["ok"] is True, result
    assert result["data"]["path"] == str(custom.resolve())
    assert api._rt.paths.resources_dir == custom.resolve() / "resources"
    assert api._rt.paths.scikit_dir == custom.resolve() / ".scikit"

    # 默认数据根是应用目录（源码=仓库根，exe=exe 同级）
    from scikit.platform import locator

    assert locator.default_dir() == app_dir()
