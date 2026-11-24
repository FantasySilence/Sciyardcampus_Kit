# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 导出动作测试：覆盖确认与 Word 产物                     #
# ================================================================== #

from __future__ import annotations

import pytest
from docx import Document

from scikit.pipeline.defaults import Tuning


def seed_session(runtime, data_root, seed_cards) -> str:
    numbers = tuple(seed_cards())
    for number in numbers:
        data_root.txt_path("选择题", number).write_text(
            f"第{number}题的题干。\n\nA 选项\n", encoding="utf-8"
        )
    items = [
        {
            "index": number,
            "number": number,
            "kind": "选择题",
            "png": data_root.rel(data_root.png_path("选择题", number)),
            "txt": data_root.rel(data_root.txt_path("选择题", number)),
            "tags": [],
            "included": True,
            "ocrError": "",
        }
        for number in numbers
    ]
    session = runtime.sessions.create({"mode": "type", "pngType": "选择题"}, items)
    return session["id"]


def test_export_creates_word(api, runtime, data_root, seed_cards, wait_job) -> None:
    session_id = seed_session(runtime, data_root, seed_cards)

    started = api.tool_call(
        "export", "start_export", {"sessionId": session_id, "filename": "选择题题库.docx"}
    )
    assert started["ok"] is True
    snapshot = wait_job(api, started["data"]["jobId"])

    assert snapshot["status"] == "done", snapshot
    assert snapshot["result"]["textCount"] == 3
    assert (data_root.word_output_dir / "选择题题库.docx").exists()


def test_export_refuses_overwrite_without_flag(
    api, runtime, data_root, seed_cards, wait_job
) -> None:
    session_id = seed_session(runtime, data_root, seed_cards)
    (data_root.word_output_dir / "选择题题库.docx").write_bytes(b"old")

    refused = api.tool_call(
        "export", "start_export", {"sessionId": session_id, "filename": "选择题题库.docx"}
    )
    assert refused["ok"] is False
    assert refused["error"]["code"] == "FILE_EXISTS"

    started = api.tool_call(
        "export",
        "start_export",
        {"sessionId": session_id, "filename": "选择题题库.docx", "overwrite": True},
    )
    assert started["ok"] is True
    snapshot = wait_job(api, started["data"]["jobId"])
    assert snapshot["status"] == "done"


def test_files_only_scope_creates_session_on_open(
    api, data_root, seed_cards, wait_job
) -> None:
    numbers = tuple(seed_cards())
    for number in numbers:
        data_root.txt_path("选择题", number).write_text("题干\n\nA 选项\n", encoding="utf-8")

    history = api.tool_call("export", "history")
    assert history["data"]["entries"][0]["source"] == "files"

    opened = api.tool_call(
        "export", "session_get", {"mode": "type", "pngType": "选择题"}
    )
    assert opened["ok"] is True
    payload = opened["data"]
    assert payload["session"]["id"]
    assert payload["session"]["source"] == "files"
    assert len(payload["session"]["items"]) == 3

    started = api.tool_call(
        "export",
        "start_export",
        {"sessionId": payload["session"]["id"], "filename": "旧产物.docx"},
    )
    assert started["ok"] is True
    snapshot = wait_job(api, started["data"]["jobId"])
    assert snapshot["status"] == "done"


def test_edit_text_writes_txt_and_export_uses_it(
    api, runtime, data_root, seed_cards, wait_job
) -> None:
    session_id = seed_session(runtime, data_root, seed_cards)
    edited = "编辑后的题干。\n\nA 新选项"

    saved = api.tool_call(
        "export",
        "save_text",
        {"sessionId": session_id, "index": 273, "text": edited},
    )
    assert saved["ok"] is True, saved
    item = next(
        item
        for item in saved["data"]["session"]["items"]
        if item["index"] == 273
    )
    assert "编辑后的题干" in item["text"]

    txt = data_root.txt_path("选择题", 273)
    assert txt.read_text(encoding="utf-8") == edited + "\n"

    # 显式选文字后，导出应使用编辑后的 txt
    changed = api.tool_call(
        "export",
        "set_render_mode",
        {"sessionId": session_id, "index": 273, "mode": "text"},
    )
    assert changed["ok"] is True
    item = next(
        item
        for item in changed["data"]["session"]["items"]
        if item["index"] == 273
    )
    assert item["exportMode"] == "text"

    started = api.tool_call(
        "export",
        "start_export",
        {"sessionId": session_id, "filename": "编辑后.docx"},
    )
    assert started["ok"] is True
    snapshot = wait_job(api, started["data"]["jobId"])
    assert snapshot["status"] == "done", snapshot

    document = Document(data_root.word_output_dir / "编辑后.docx")
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    assert "编辑后的题干。" in paragraphs
    assert "A 新选项" in paragraphs


def test_reocr_single_item(
    api, runtime, data_root, seed_cards, wait_job, tesseract
) -> None:
    try:
        tesseract.prepare()
    except Exception as error:  # noqa: BLE001
        pytest.skip(str(error))

    session_id = seed_session(runtime, data_root, seed_cards)
    started = api.tool_call(
        "export", "start_ocr", {"sessionId": session_id, "indexes": [273]}
    )
    assert started["ok"] is True
    snapshot = wait_job(api, started["data"]["jobId"])
    assert snapshot["status"] == "done", snapshot
    assert snapshot["result"]["stats"]["ok"] == 1

    loaded = api.tool_call("export", "session_get", {"sessionId": session_id})
    item = next(
        item for item in loaded["data"]["session"]["items"] if item["index"] == 273
    )
    assert item["txt"]
    assert item["text"]


def test_default_filename_uses_suffix() -> None:
    from scikit.pipeline.docx import default_filename

    tuning = Tuning()
    assert (
        default_filename({"mode": "type", "pngType": "选择题"}, tuning)
        == "选择题题库.docx"
    )
    assert default_filename({"mode": "paper", "paper": "期中卷"}, tuning) == "期中卷.docx"


def test_set_all_render_mode_action(
    api, runtime, data_root, seed_cards
) -> None:
    """一键全部文字 / 全部图片：整卷生效并回传新统计。"""

    session_id = seed_session(runtime, data_root, seed_cards)

    result = api.tool_call(
        "export", "set_all_render_mode", {"sessionId": session_id, "mode": "image"}
    )
    assert result["ok"] is True, result
    data = result["data"]
    assert data["changed"] == "image"
    assert data["count"] == 3
    assert {item["exportMode"] for item in data["session"]["items"]} == {"image"}
    assert data["stats"]["imageCount"] == 3
    assert data["stats"]["textCount"] == 0

    back = api.tool_call(
        "export", "set_all_render_mode", {"sessionId": session_id, "mode": "text"}
    )
    assert back["data"]["stats"]["textCount"] == 3

    refused = api.tool_call(
        "export", "set_all_render_mode", {"sessionId": session_id, "mode": "auto"}
    )
    assert refused["ok"] is False
    assert refused["error"]["code"] == "INVALID_INPUT"


def test_preview_word_describes_export_without_writing(
    api, runtime, data_root, seed_cards
) -> None:
    """预览只读：给出与导出同源的题目计划，且不生成 docx。"""

    session_id = seed_session(runtime, data_root, seed_cards)
    preview = api.tool_call("export", "preview_word", {"sessionId": session_id})
    assert preview["ok"] is True, preview
    data = preview["data"]

    assert data["textCount"] == 3
    assert data["imageCount"] == 0
    assert [question["index"] for question in data["questions"]] == [273, 274, 275]
    first = data["questions"][0]
    assert first["title"] == "第273题"
    assert first["mode"] == "text"
    assert first["paragraphs"][0].startswith("第273题的题干")
    assert data["font"]
    assert data["page"]["widthCm"] > 0
    # 预览不落盘
    assert not (data_root.word_output_dir / data["filename"]).exists()


def test_preview_word_follows_included_and_render_mode(
    api, runtime, data_root, seed_cards
) -> None:
    session_id = seed_session(runtime, data_root, seed_cards)
    api.tool_call(
        "export",
        "session_update",
        {"sessionId": session_id, "included": {"273": False}},
    )
    api.tool_call(
        "export",
        "set_render_mode",
        {"sessionId": session_id, "index": 274, "mode": "image"},
    )

    data = api.tool_call("export", "preview_word", {"sessionId": session_id})["data"]

    assert [question["index"] for question in data["questions"]] == [274, 275]
    assert data["total"] == 2
    assert data["textCount"] == 1
    assert data["imageCount"] == 1
    image_question = data["questions"][0]
    assert image_question["mode"] == "image"
    assert image_question["png"].endswith("274.png")


def test_preview_word_reports_missing_text_fallback(
    api, runtime, data_root, seed_cards
) -> None:
    session_id = seed_session(runtime, data_root, seed_cards)
    data_root.txt_path("选择题", 274).unlink()

    data = api.tool_call("export", "preview_word", {"sessionId": session_id})["data"]

    fallback = next(question for question in data["questions"] if question["index"] == 274)
    assert fallback["mode"] == "image"
    assert any("274" in warning["text"] for warning in data["warnings"])
    assert data["warnings"][0]["level"] == "warn"

