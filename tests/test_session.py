# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 检查会话仓储测试                                       #
# ================================================================== #

from __future__ import annotations

import pytest

from scikit.errors import AppError
from scikit.session import SessionStore


def make_items() -> list[dict]:
    return [
        {
            "index": 273,
            "number": 273,
            "kind": "选择题",
            "png": "resources/row_pngs/选择题/273.png",
            "txt": "resources/row_txt/选择题/273.txt",
            "tags": [],
            "included": True,
            "ocrError": "",
        },
        {
            "index": 274,
            "number": 274,
            "kind": "选择题",
            "png": "resources/row_pngs/选择题/274.png",
            "txt": "resources/row_txt/选择题/274_formula.txt",
            "tags": ["formula"],
            "included": True,
            "ocrError": "",
        },
    ]


def test_create_and_load_session(data_root) -> None:
    store = SessionStore(data_root.sessions_dir)
    session = store.create({"mode": "type", "pngType": "选择题"}, make_items())
    assert session["stats"]["total"] == 2
    assert session["stats"]["included"] == 2
    assert session["stats"]["formula"] == 1

    loaded = store.load(session["id"])
    assert loaded["scope"]["pngType"] == "选择题"
    assert len(loaded["items"]) == 2


def test_update_included_recomputes_stats(data_root) -> None:
    store = SessionStore(data_root.sessions_dir)
    session = store.create({"mode": "type", "pngType": "选择题"}, make_items())
    updated = store.update_included(session["id"], {"273": False})
    assert updated["stats"]["included"] == 1
    assert updated["stats"]["excluded"] == 1


def test_latest_for_scope(data_root) -> None:
    store = SessionStore(data_root.sessions_dir)
    first = store.create({"mode": "type", "pngType": "选择题"}, make_items())
    second = store.create({"mode": "type", "pngType": "选择题"}, make_items())
    assert store.latest_for_scope({"mode": "type", "pngType": "选择题"})["id"] == second["id"]
    assert first["id"] != second["id"]


def test_invalid_id_is_rejected(data_root) -> None:
    store = SessionStore(data_root.sessions_dir)
    with pytest.raises(AppError) as error:
        store.load("../evil")
    assert error.value.code == "INVALID_SESSION"


def test_export_mode_defaults_to_auto_and_can_change(data_root) -> None:
    store = SessionStore(data_root.sessions_dir)
    session = store.create({"mode": "type", "pngType": "选择题"}, make_items())
    assert session["items"][0]["exportMode"] == "auto"

    updated = store.set_render_mode(session["id"], 273, "text")
    assert updated["items"][0]["exportMode"] == "text"
    assert updated["items"][1]["exportMode"] == "auto"

    with pytest.raises(AppError) as error:
        store.set_render_mode(session["id"], 273, "bogus")
    assert error.value.code == "INVALID_INPUT"
