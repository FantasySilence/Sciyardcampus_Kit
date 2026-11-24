# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 设备协议：截图、滑动、点击的最小接口                    #
# ================================================================== #
# 采集流水线只依赖这个协议，不关心背后是 adb 还是鼠标。
# 测试里用 FakeDevice 按脚本返回帧，就能离线验证状态机。

from __future__ import annotations

from typing import Protocol

from PIL import Image


class Device(Protocol):
    """采集需要的设备能力。"""

    channel: str

    def describe(self) -> dict:
        """返回前端要显示的设备信息（通道、序列号、窗口等）。"""

    def capture(self) -> Image.Image:
        """截一张 1600x900（或配置分辨率）的整屏。"""

    def swipe(self, pixels: int) -> None:
        """滑动指定虚拟机像素；正数向下、负数向上。"""

    def tap(self, x: int, y: int) -> None:
        """点击虚拟机坐标。"""

    def close(self) -> None:
        """释放资源（当前实现为空，保留扩展点）。"""
