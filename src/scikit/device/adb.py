# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: adb 通道：设备探测、连接、截图、滑动、点击              #
# ================================================================== #
# 与上游的区别：
#   - 所有子进程隐藏控制台窗口（CREATE_NO_WINDOW）并带超时；
#   - 截图失败直接报错，不再静默退回鼠标通道。桌面应用点“开始”时
#     自己的窗口在最前面，鼠标截到的模拟器往往被遮挡，静默兜底只会
#     让用户拿到一堆错图。

from __future__ import annotations

import io
import os
import shutil
import subprocess
import time
from pathlib import Path

from PIL import Image

from scikit import const
from scikit.errors import AppError
from scikit.pipeline.defaults import Tuning


class AdbDevice:
    """通过 adb 操作安卓模拟器。"""

    channel = "adb"

    def __init__(
        self,
        adb_path: str,
        serial: str | None,
        tuning: Tuning,
        reporter=None,
    ) -> None:
        self._adb = adb_path
        self._configured_serial = (serial or "").strip() or None
        self._tuning = tuning
        self._reporter = reporter
        self._serial: str | None = None

    # ------ 探测 ------ #
    @staticmethod
    def locate(configured: str = "") -> str | None:
        """按“设置里的路径 → PATH → 常见安装位置”找 adb.exe。"""

        value = (configured or "").strip()
        if value:
            path = Path(value)
            if path.exists():
                return str(path)
            # 用户填了路径但不存在：不悄悄换别的 adb，交给上层报错
            raise AppError(
                "ADB_PATH_INVALID",
                "设置里的 adb 路径不存在",
                value,
            )
        found = shutil.which("adb")
        if found:
            return found
        for candidate in const.ADB_CANDIDATES:
            if os.path.exists(candidate):
                return candidate
        return None

    def _run(
        self, args: list[str], timeout: int = 15, check: bool = False
    ) -> subprocess.CompletedProcess:
        """执行 adb 命令，统一隐藏窗口、捕获输出、带超时。"""

        command = [self._adb]
        if self._serial:
            command += ["-s", self._serial]
        command += args
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                timeout=timeout,
                creationflags=const.CREATE_NO_WINDOW,
            )
        except subprocess.TimeoutExpired as error:
            raise AppError(
                "ADB_TIMEOUT", "adb 命令超时", f"{' '.join(args)}（{timeout}s）"
            ) from error
        except OSError as error:
            raise AppError("ADB_FAILED", "无法启动 adb", str(error)) from error
        if check and result.returncode != 0:
            detail = result.stderr.decode("utf-8", "replace").strip()
            raise AppError(
                "ADB_FAILED",
                "adb 命令失败",
                f"{' '.join(args)}：{detail[-const.ADB_ERROR_DETAIL_LIMIT:]}",
            )
        return result

    def devices(self) -> list[str]:
        """返回状态为 device 的设备序列号列表。"""

        result = self._run(["devices"])
        devices: list[str] = []
        for line in result.stdout.decode("utf-8", "replace").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices

    def connect(self, address: str) -> dict:
        """执行 adb connect，再刷新设备列表。"""

        address = (address or "").strip()
        if not address:
            raise AppError("INVALID_INPUT", "请填写模拟器 adb 地址")
        result = self._run(["connect", address], timeout=const.ADB_CONNECT_TIMEOUT)
        output = (result.stdout + result.stderr).decode("utf-8", "replace").strip()
        devices = self.devices()
        return {"address": address, "output": output, "devices": devices}

    def restart_server(self) -> dict:
        """重启 adb server：设备列表异常时的修复手段。"""

        self._run(["kill-server"], timeout=const.ADB_TIMEOUT)
        self._run(["start-server"], timeout=const.ADB_SERVER_TIMEOUT)
        return {"devices": self.devices()}

    def resolve_serial(self) -> str:
        """确定用哪台设备：设置优先；多设备优先 127.0.0.1:*。"""

        if self._configured_serial:
            self._serial = self._configured_serial
            return self._serial

        devices = self.devices()
        if not devices:
            raise AppError(
                "ADB_NO_DEVICE",
                "adb 没有可用设备",
                "请先启动模拟器，再点“连接模拟器”；MuMu 默认地址 127.0.0.1:16384",
            )
        if len(devices) == 1:
            self._serial = devices[0]
        else:
            network = [
                name
                for name in devices
                if name.startswith(const.ADB_NETWORK_PREFIXES)
            ]
            self._serial = network[0] if network else devices[0]
            if self._reporter is not None:
                self._reporter.log(
                    f"adb 检测到 {len(devices)} 个设备，使用 {self._serial}", "warn"
                )
        return self._serial

    # ------ 截图 / 交互 ------ #
    def capture(self) -> Image.Image:
        """截一张原生分辨率整屏；失败直接抛错，不退回鼠标。"""

        self.resolve_serial()
        result = self._run(
            ["exec-out", "screencap", "-p"], timeout=const.ADB_CAPTURE_TIMEOUT
        )
        if result.returncode != 0 or not result.stdout:
            detail = result.stderr.decode("utf-8", "replace").strip()
            raise AppError(
                "ADB_CAPTURE_FAILED",
                "adb 截图失败",
                detail[-const.ADB_ERROR_DETAIL_LIMIT:]
                or "请确认模拟器已启动、设备已连接",
            )
        try:
            return Image.open(io.BytesIO(result.stdout)).convert("RGB")
        except Exception as error:  # noqa: BLE001 - 返回的字节不是有效图片
            raise AppError(
                "ADB_CAPTURE_FAILED", "adb 截图数据无法解析", str(error)
            ) from error

    def chunks(self, pixels: int) -> list[tuple[int, int]]:
        """把一次滑动拆成不超过画面高度 60% 的若干段，丢掉太短的尾巴。"""

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

    def start_point(self, direction: int) -> tuple[int, int]:
        """按方向取滑动起点，避免终点被画面边界截短。"""

        x = int(self._tuning.screen_width * self._tuning.start_x_ratio)
        ratio = (
            self._tuning.start_y_ratio
            if direction > 0
            else 1 - self._tuning.start_y_ratio
        )
        return x, int(self._tuning.screen_height * ratio)

    def duration_for(self, pixels: int) -> int:
        """按距离给滑动时长；太短会被 Android 当成“长按”。"""

        duration = abs(int(pixels)) * self._tuning.adb_ms_per_pixel
        return max(
            self._tuning.adb_min_duration,
            min(self._tuning.adb_duration, duration),
        )

    def swipe(self, pixels: int) -> None:
        """滑动指定虚拟机像素；正数向下、负数向上。"""

        for direction, step in self.chunks(pixels):
            self._swipe_once(step, direction)
            self._sleep(const.ADB_SWIPE_PAUSE)

    def _swipe_once(self, pixels: int, direction: int) -> None:
        """执行一次 input swipe。"""

        start_x, start_y = self.start_point(direction)
        end_y = max(
            const.ADB_EDGE_MARGIN,
            min(
                start_y - direction * pixels,
                self._tuning.screen_height - const.ADB_EDGE_MARGIN,
            ),
        )
        duration = self.duration_for(end_y - start_y)
        self._run(
            [
                "shell",
                "input",
                "swipe",
                str(start_x),
                str(start_y),
                str(start_x),
                str(end_y),
                str(duration),
            ],
            timeout=const.ADB_SWIPE_TIMEOUT,
            check=True,
        )
        if self._reporter is not None:
            self._reporter.log(
                f"adb 滑动 {pixels} 像素，({start_x}, {start_y}) -> ({start_x}, {end_y})，{duration}ms",
                "info",
            )

    def tap(self, x: int, y: int) -> None:
        """点击虚拟机坐标。"""

        self._run(
            ["shell", "input", "tap", str(int(x)), str(int(y))],
            timeout=const.ADB_TAP_TIMEOUT,
            check=False,
        )

    def describe(self) -> dict:
        """给前端显示的设备信息。"""

        return {
            "channel": "adb",
            "adb": self._adb,
            "serial": self._serial or self._configured_serial or "",
        }

    def close(self) -> None:
        """adb 通道没有需要释放的长期资源。"""

    # ------ 内部 ------ #
    def _sleep(self, seconds: float) -> None:
        """优先用 Reporter 的可取消等待。"""

        if self._reporter is not None:
            self._reporter.sleep(seconds)
        else:
            time.sleep(seconds)
