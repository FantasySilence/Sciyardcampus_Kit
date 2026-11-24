# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 鼠标兜底通道：截模拟器窗口 + 拖拽滑动                   #
# ================================================================== #
# 只在没有 adb、且用户显式打开“允许鼠标兜底”时使用。
# 运行期间必须让模拟器窗口保持可见；应用会先最小化自己再倒计时。

from __future__ import annotations

import time
from collections.abc import Iterable

from PIL import Image

from scikit import const
from scikit.device.screen import EmulatorScreen
from scikit.errors import AppError
from scikit.pipeline.defaults import Tuning


class MouseDevice:
    """通过 pyautogui 截窗口、拖拽、点击。"""

    channel = "mouse"

    def __init__(
        self,
        tuning: Tuning,
        reporter=None,
        keywords: Iterable[str] = const.WINDOW_TITLE_KEYWORDS,
    ) -> None:
        self._tuning = tuning
        self._reporter = reporter
        self._keywords = tuple(keywords)
        self._box: tuple[int, int, int, int] | None = None

    # ------ 窗口 ------ #
    def box(self) -> tuple[int, int, int, int]:
        """缓存模拟器窗口位置；窗口移动后需要重新创建设备对象。"""

        if self._box is None:
            self._box = EmulatorScreen.window_box(self._tuning, self._keywords)
            if self._reporter is not None:
                left, top, width, height = self._box
                scale = EmulatorScreen.scale(self._box, self._tuning)
                self._reporter.log(
                    f"鼠标通道：窗口 ({left}, {top}) {width}x{height}，缩放 {scale:.3f}",
                    "warn",
                )
                self._reporter.log(
                    "运行期间不要让其它窗口挡住模拟器画面", "warn"
                )
        return self._box

    # ------ 截图 / 交互 ------ #
    def capture(self) -> Image.Image:
        """截模拟器窗口；返回的图可能带缩放，切题逻辑会按宽度换算。"""

        import pyautogui

        EmulatorScreen.enable_dpi_awareness()
        try:
            return pyautogui.screenshot(region=self.box()).convert("RGB")
        except Exception as error:  # noqa: BLE001
            raise AppError("MOUSE_CAPTURE_FAILED", "鼠标截图失败", str(error)) from error

    def chunks(self, pixels: int) -> list[tuple[int, int]]:
        """按虚拟机像素拆成多段拖拽。"""

        limit = int(self._tuning.screen_height * self._tuning.max_swipe_ratio)
        direction = 1 if pixels >= 0 else -1
        remaining = abs(int(pixels))
        steps: list[tuple[int, int]] = []
        while remaining > 0:
            step = min(remaining, limit)
            steps.append((direction, step))
            remaining -= step
        while len(steps) > 1 and steps[-1][1] < const.ADB_MIN_CHUNK_PIXELS:
            steps.pop()
        return steps

    def swipe(self, pixels: int) -> None:
        """分段拖拽。"""

        for direction, step in self.chunks(pixels):
            self._drag(step, direction)
            self._sleep(const.ADB_SWIPE_PAUSE)

    def _drag(self, pixels: int, direction: int) -> None:
        """按住 -> 匀速拖动 -> 停顿 -> 松手，避免惯性甩屏。"""

        import pyautogui

        box = self.box()
        start_x_emu = int(self._tuning.screen_width * self._tuning.start_x_ratio)
        ratio = (
            self._tuning.start_y_ratio
            if direction > 0
            else 1 - self._tuning.start_y_ratio
        )
        start_y_emu = int(self._tuning.screen_height * ratio)
        end_y_emu = start_y_emu - direction * pixels
        end_y_emu = max(
            const.ADB_EDGE_MARGIN,
            min(
                end_y_emu,
                self._tuning.screen_height - const.ADB_EDGE_MARGIN,
            ),
        )

        start_x, start_y = EmulatorScreen.to_screen(
            start_x_emu, start_y_emu, box, self._tuning
        )
        end_x, end_y = EmulatorScreen.to_screen(
            start_x_emu, end_y_emu, box, self._tuning
        )

        pyautogui.moveTo(start_x, start_y, _pause=False)
        time.sleep(const.MOUSE_MOVE_PAUSE)
        pyautogui.mouseDown(x=start_x, y=start_y, _pause=False)
        steps = max(
            const.MOUSE_MIN_STEPS,
            abs(end_y - start_y) // const.MOUSE_STEP_PIXELS,
        )
        for index in range(1, steps + 1):
            ratio = index / steps
            pyautogui.moveTo(
                int(round(start_x + (end_x - start_x) * ratio)),
                int(round(start_y + (end_y - start_y) * ratio)),
                _pause=False,
            )
            time.sleep(self._tuning.drag_duration / steps)
        time.sleep(self._tuning.hold_before_release)
        pyautogui.mouseUp(x=end_x, y=end_y, _pause=False)
        if self._reporter is not None:
            self._reporter.log(
                f"拖拽 {pixels} 像素，({start_x}, {start_y}) -> ({end_x}, {end_y})",
                "info",
            )

    def tap(self, x: int, y: int) -> None:
        """点击虚拟机坐标。"""

        import pyautogui

        screen_x, screen_y = EmulatorScreen.to_screen(x, y, self.box(), self._tuning)
        pyautogui.click(screen_x, screen_y)

    def describe(self) -> dict:
        """给前端显示的设备信息。"""

        try:
            box = self.box()
        except AppError:
            box = None
        return {
            "channel": "mouse",
            "window": box,
        }

    def close(self) -> None:
        """鼠标通道没有长期资源。"""

    # ------ 内部 ------ #
    def _sleep(self, seconds: float) -> None:
        if self._reporter is not None:
            self._reporter.sleep(seconds)
        else:
            time.sleep(seconds)
