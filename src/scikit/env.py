# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 环境自检：adb / Tesseract / 数据目录                    #
# ================================================================== #
# 只做只读探测，不改数据；前端顶栏状态灯和设置页的“环境自检”都走这里。

from __future__ import annotations

from typing import Any

from scikit.device import describe_adb
from scikit.errors import AppError
from scikit.pipeline.defaults import Tuning
from scikit.pipeline.ocr import TesseractOcr
from scikit.platform.schema import get_path


class Environment:
    """设备与 OCR 的探测门面。"""

    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime

    def check(self, settings: dict) -> dict:
        """返回 adb、Tesseract、数据目录三块状态；单项失败不影响其它项。"""

        tuning = Tuning.from_settings(settings)
        data = self._runtime.location.to_dict()

        adb = describe_adb(settings)
        tesseract = self._check_tesseract(settings, tuning)

        return {
            "data": data,
            "adb": adb,
            "tesseract": tesseract,
            "mouse": {
                "enabled": bool(get_path(settings, "device.allowMouseFallback", False)),
            },
        }

    def connect(self, address: str, settings: dict) -> dict:
        """执行 adb connect；地址为空时用设置里的默认地址。"""

        from scikit.device.adb import AdbDevice

        configured = str(get_path(settings, "device.adbPath", "") or "")
        serial = str(get_path(settings, "device.serial", "") or "")
        target = (address or str(get_path(settings, "device.connectAddress", "") or "")).strip()
        if not target:
            raise AppError("INVALID_INPUT", "请填写模拟器 adb 地址")

        adb_path = AdbDevice.locate(configured)
        if not adb_path:
            raise AppError(
                "ADB_NOT_FOUND",
                "没有找到 adb",
                "请先在设置里指定模拟器自带的 adb.exe",
            )
        device = AdbDevice(adb_path, serial, Tuning.from_settings(settings))
        result = device.connect(target)
        return {
            "address": result["address"],
            "output": result["output"],
            "devices": result["devices"],
        }

    def _check_tesseract(self, settings: dict, tuning: Tuning) -> dict:
        """检查 tesseract 是否存在、版本、语言包；任何失败都转成结构化状态。"""

        path = str(get_path(settings, "ocr.tesseractPath", "") or "")
        client = TesseractOcr(path, self._runtime.paths.tmp_dir, timeout=tuning.ocr_timeout)
        try:
            info = client.prepare()
            missing = [
                name
                for name in tuning.ocr_lang.split("+")
                if name and name not in info["langs"]
            ]
            return {
                "ok": not missing,
                "path": info["path"],
                "version": info["version"],
                "langs": info["langs"],
                "missing": missing,
                "error": "",
            }
        except AppError as error:
            return {
                "ok": False,
                "path": path,
                "version": "",
                "langs": [],
                "missing": [],
                "error": error.message,
                "detail": error.detail,
            }
