# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 采集状态机测试：假设备 + 真实 OCR，不出模拟器           #
# ================================================================== #

from __future__ import annotations

import pytest

from scikit.tools.export import actions


@pytest.mark.ocr
def test_capture_type_with_fake_device(
    api, data_root, fake_device, monkeypatch, wait_job, tesseract
) -> None:
    # OCR 不可用时跳过，避免在没装 Tesseract 的机器上失败
    try:
        tesseract.prepare()
    except Exception as error:  # noqa: BLE001
        pytest.skip(str(error))

    # 采集时不要真的等 warmup，也不要访问 adb
    settings = api.settings_get("export")["data"]
    settings["capture"]["warmup"] = 0
    assert api.settings_save("export", settings)["ok"] is True

    monkeypatch.setattr(
        actions, "create_device", lambda settings, tuning, reporter: fake_device
    )

    started = api.tool_call(
        "export",
        "start_capture",
        {"mode": "type", "pngType": "选择题", "pages": 5, "clearOld": True},
    )
    assert started["ok"] is True, started
    snapshot = wait_job(api, started["data"]["jobId"])

    assert snapshot["status"] == "done", snapshot
    assert snapshot["result"]["captured"] == 2
    assert snapshot["result"]["ocr"]["ok"] == 2

    session_id = snapshot["result"]["sessionId"]
    loaded = api.tool_call("export", "session_get", {"sessionId": session_id})
    assert loaded["ok"] is True
    items = loaded["data"]["session"]["items"]
    assert [item["index"] for item in items] == [21, 22]
    assert all(item["txt"] for item in items)
    assert len(list(data_root.row_txt_dir.glob("选择题/*.txt"))) == 2


@pytest.mark.ocr
def test_probe_returns_cards(
    api, fake_device, monkeypatch, wait_job, tesseract
) -> None:
    try:
        tesseract.prepare()
    except Exception as error:  # noqa: BLE001
        pytest.skip(str(error))

    monkeypatch.setattr(
        actions, "create_device", lambda settings, tuning, reporter: fake_device
    )
    started = api.tool_call("export", "probe")
    snapshot = wait_job(api, started["data"]["jobId"])

    assert snapshot["status"] == "done"
    assert len(snapshot["result"]["cards"]) == 2
    assert snapshot["result"]["frame"].startswith(".scikit/probe/")
