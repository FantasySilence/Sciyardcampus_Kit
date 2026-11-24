# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: pytest 公共夹具：路径、运行时、假设备、测试素材         #
# ================================================================== #

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest
from PIL import Image

# 源码运行时把 src/ 加进搜索路径；测试不依赖安装包
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scikit.api import Api  # noqa: E402
from scikit.env import Environment  # noqa: E402
from scikit.jobs import JobManager  # noqa: E402
from scikit.pipeline.artifact_paths import ArtifactPaths  # noqa: E402
from scikit.pipeline.defaults import Tuning  # noqa: E402
from scikit.pipeline.ocr import TesseractOcr  # noqa: E402
from scikit.platform import locator  # noqa: E402
from scikit.platform.storage import Runtime  # noqa: E402
from scikit.platform.store import Store  # noqa: E402
from scikit.session import SessionStore  # noqa: E402
from scikit.tools import build_registry  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def tuning() -> Tuning:
    """默认算法参数；warmup 改 0，测试不要真的等 2 秒。"""

    return Tuning(warmup=0)


@pytest.fixture
def data_root(tmp_path: Path) -> ArtifactPaths:
    """临时数据根，布局与真实应用一致。"""

    paths = ArtifactPaths(tmp_path)
    paths.ensure()
    return paths


@pytest.fixture
def runtime(data_root: ArtifactPaths) -> Runtime:
    """最小运行时：真实 Store / SessionStore / JobManager / Environment。"""

    location = locator.Location(path=data_root.root, source="cli", writable=True)
    runtime = Runtime(
        location=location,
        store=Store(data_root.root / ".scikit"),
        paths=data_root,
        jobs=JobManager(),
        sessions=SessionStore(data_root.sessions_dir),
        env=None,
        webview_dir=data_root.root / "webview",
    )
    runtime.env = Environment(runtime)
    return runtime


@pytest.fixture
def api(runtime: Runtime) -> Api:
    """带两个工具注册表的 Api 门面。"""

    return Api(runtime, build_registry())


@pytest.fixture
def tesseract(data_root: ArtifactPaths) -> TesseractOcr:
    """真实 Tesseract；只给标记了 ocr 的测试用。"""

    return TesseractOcr("", data_root.tmp_dir, timeout=60)


@pytest.fixture
def wait_job():
    """轮询任务直到终态，返回最后一次 snapshot。"""

    def wait(api: Api, job_id: str, timeout: float = 60.0) -> dict:
        import time

        deadline = time.time() + timeout
        since = 0
        while time.time() < deadline:
            result = api.job_status(job_id, since)
            assert result["ok"], result
            snapshot = result["data"]
            if snapshot["logs"]:
                since = snapshot["logs"][-1]["seq"]
            if snapshot["status"] != "running":
                return snapshot
            time.sleep(0.05)
        raise AssertionError(f"job {job_id} 超时未结束")

    return wait


class FakeDevice:
    """按脚本返回同一张整屏的假设备，记录 swipe/tap 调用。"""

    channel = "adb"

    def __init__(self, frame: Image.Image) -> None:
        self._frame = frame.convert("RGB")
        self.swipes: list[int] = []
        self.taps: list[tuple[int, int]] = []

    def describe(self) -> dict:
        return {"channel": "fake"}

    def capture(self) -> Image.Image:
        return self._frame.copy()

    def swipe(self, pixels: int) -> None:
        self.swipes.append(int(pixels))

    def tap(self, x: int, y: int) -> None:
        self.taps.append((int(x), int(y)))

    def close(self) -> None:
        return


@pytest.fixture
def probe_frame() -> Image.Image:
    """上游留下的一张 1600x900 整屏，里面有两张完整题卡。"""

    return Image.open(FIXTURES / "probe.png").convert("RGB")


@pytest.fixture
def fake_device(probe_frame: Image.Image) -> FakeDevice:
    """返回这张整屏的假设备。"""

    return FakeDevice(probe_frame)


@pytest.fixture
def seed_cards(data_root: ArtifactPaths):
    """把 273/274/275 三张题卡复制进 row_pngs/选择题，返回题号列表。"""

    def seed(numbers: tuple[int, ...] = (273, 274, 275)) -> list[int]:
        folder = data_root.type_dir("选择题")
        for number in numbers:
            shutil.copy2(FIXTURES / f"card-{number}.png", folder / f"{number}.png")
        return list(numbers)

    return seed
