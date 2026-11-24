# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 设备工厂：按设置选 adb 或鼠标通道                       #
# ================================================================== #

from __future__ import annotations

from scikit import const
from scikit.device.adb import AdbDevice
from scikit.device.base import Device
from scikit.device.mouse import MouseDevice
from scikit.errors import AppError
from scikit.pipeline.defaults import Tuning, split_list
from scikit.platform.schema import get_path


def create_device(settings: dict, tuning: Tuning, reporter=None) -> Device:
    """
    根据设置创建设备对象。

    规则：
        - 找到 adb 且至少有一台设备 -> adb 通道；
        - 没有 adb 或没有设备，且显式允许鼠标兜底 -> 鼠标通道；
        - 否则抛错，让用户去连接模拟器，而不是悄悄截出被遮挡的画面。
    """

    configured = str(get_path(settings, "device.adbPath", "") or "")
    serial = str(get_path(settings, "device.serial", "") or "")
    allow_mouse = bool(get_path(settings, "device.allowMouseFallback", False))

    adb_path = AdbDevice.locate(configured)
    if adb_path:
        device = AdbDevice(adb_path, serial, tuning, reporter)
        devices = device.devices()
        if devices:
            return device
        if not allow_mouse:
            raise AppError(
                "ADB_NO_DEVICE",
                "adb 没有可用设备",
                "请先启动模拟器，再点“连接模拟器”；MuMu 默认地址 127.0.0.1:16384",
            )
        if reporter is not None:
            reporter.log("adb 没有设备，按设置改用鼠标通道", "warn")

    if allow_mouse:
        keywords = split_list(
            str(get_path(settings, "device.windowKeywords", "") or ""),
            const.WINDOW_TITLE_KEYWORDS,
        )
        return MouseDevice(tuning, reporter, keywords)

    raise AppError(
        "ADB_NOT_FOUND",
        "没有找到 adb，且未允许鼠标兜底",
        "请在设置里指定模拟器自带的 adb.exe，例如 MuMu 的 ...\\shell\\adb.exe",
    )


def describe_adb(settings: dict) -> dict:
    """
    只做轻量探测，不创建设备、不截图。

    env_check / 顶栏状态灯用；设备列表为空时也正常返回。
    """

    configured = str(get_path(settings, "device.adbPath", "") or "")
    serial = str(get_path(settings, "device.serial", "") or "")
    try:
        adb_path = AdbDevice.locate(configured)
    except AppError as error:
        return {"found": False, "path": configured, "devices": [], "error": error.message}

    if not adb_path:
        return {"found": False, "path": "", "devices": [], "error": "没有找到 adb"}

    probe = AdbDevice(adb_path, serial, Tuning())
    try:
        devices = probe.devices()
    except AppError as error:
        return {"found": True, "path": adb_path, "devices": [], "error": error.message}
    return {
        "found": True,
        "path": adb_path,
        "devices": devices,
        "selected": serial or (devices[0] if len(devices) == 1 else ""),
        "error": "",
    }
