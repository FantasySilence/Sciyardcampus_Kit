# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 模拟器窗口与屏幕坐标（鼠标兜底通道用）                 #
# ================================================================== #
# adb 通道直接拿原生分辨率，完全不需要这里；
# 只有没有 adb、退回鼠标截图/拖拽时才要认窗口、算缩放。
# 上游用 Win32 DPI 感知 + pygetwindow 找窗口，这里保持同样的思路。

from __future__ import annotations

import sys
from collections.abc import Iterable

from scikit import const
from scikit.errors import AppError
from scikit.pipeline.defaults import Tuning

# DPI 感知只需要设置一次
_dpi_ready = False


class EmulatorScreen:
    """模拟器窗口的位置、缩放与坐标换算。"""

    @staticmethod
    def enable_dpi_awareness() -> None:
        """
        声明进程 DPI 感知。

        不做这一步时，Windows 缩放不是 100% 的情况下，pyautogui 拿到的
        屏幕尺寸、鼠标坐标和截图区域都会对不上。
        """

        global _dpi_ready
        if _dpi_ready or sys.platform != "win32":
            return
        _dpi_ready = True
        try:
            import ctypes

            # 2 = PROCESS_PER_MONITOR_DPI_AWARE
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:  # noqa: BLE001 - 老系统没有 shcore，忽略即可
            try:
                import ctypes

                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:  # noqa: BLE001
                pass

    @staticmethod
    def find_window(
        keywords: Iterable[str] = const.WINDOW_TITLE_KEYWORDS,
    ):
        """
        找面积最大的模拟器窗口。

        返回 pygetwindow 的窗口对象；找不到时抛 AppError，
        由上层提示“用 adb 或先打开模拟器”，不做静默兜底。
        """

        try:
            import pygetwindow as gw
        except ImportError as error:
            raise AppError(
                "PYGETWINDOW_MISSING",
                "缺少 pygetwindow，无法使用鼠标通道",
                "请重新安装依赖",
            ) from error

        names = tuple(name.lower() for name in keywords if name)
        candidates = []
        for window in gw.getAllWindows():
            title = (window.title or "").strip()
            if not title or not window.visible:
                continue
            if any(name in title.lower() for name in names):
                if window.width > 0 and window.height > 0:
                    candidates.append(window)
        if not candidates:
            raise AppError(
                "EMULATOR_WINDOW_NOT_FOUND",
                "没有找到模拟器窗口",
                "请打开模拟器，或改用 adb 通道；也可以在设置里补充窗口标题关键字",
            )
        return max(candidates, key=lambda item: item.width * item.height)

    @staticmethod
    def window_box(
        tuning: Tuning,
        keywords: Iterable[str] = const.WINDOW_TITLE_KEYWORDS,
    ) -> tuple[int, int, int, int]:
        """返回窗口客户区的 (left, top, width, height)。"""

        EmulatorScreen.enable_dpi_awareness()
        window = EmulatorScreen.find_window(keywords)
        box = (int(window.left), int(window.top), int(window.width), int(window.height))
        if (
            box[2] < const.MOUSE_MIN_WINDOW_WIDTH
            or box[3] < const.MOUSE_MIN_WINDOW_HEIGHT
        ):
            raise AppError(
                "EMULATOR_WINDOW_TOO_SMALL",
                "模拟器窗口太小",
                f"当前窗口 {box[2]}x{box[3]}，请放大到接近 {tuning.screen_width}x{tuning.screen_height}",
            )
        return box

    @staticmethod
    def scale(
        box: tuple[int, int, int, int], tuning: Tuning
    ) -> float:
        """窗口宽度 / 模拟器逻辑宽度，用于坐标换算。"""

        return box[2] / tuning.screen_width

    @staticmethod
    def to_screen(
        x: int, y: int, box: tuple[int, int, int, int], tuning: Tuning
    ) -> tuple[int, int]:
        """虚拟机坐标 -> 屏幕坐标。"""

        factor = EmulatorScreen.scale(box, tuning)
        return (
            int(round(box[0] + x * factor)),
            int(round(box[1] + y * factor)),
        )
