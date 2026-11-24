# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: Tesseract CLI 封装：隐藏子进程窗口、超时、语言包检查    #
# ================================================================== #
# 为什么不用 pytesseract：
#   1. 它的 subprocess 没有 CREATE_NO_WINDOW，打包成无控制台程序后
#      每识别一题都可能闪一次黑框；
#   2. 需要统一超时、错误码和 stderr 细节；
#   3. 需要显式检查 chi_sim 语言包是否存在。
# 接口保持成一个很小的 OcrClient 协议，测试里可以换成 FakeOcr。

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Protocol

from PIL import Image

from scikit import const
from scikit.errors import AppError


class OcrClient(Protocol):
    """流水线依赖的最小 OCR 接口。"""

    def text(self, image: Image.Image, lang: str | None = None, config: str | None = None) -> str:
        """识别一张图片，返回纯文本。"""


class TesseractOcr:
    """基于 tesseract.exe 的 OCR 客户端。"""

    def __init__(
        self,
        exe_path: str | Path | None,
        tmp_dir: str | Path,
        *,
        timeout: int = 60,
    ) -> None:
        self._configured_path = str(exe_path or "").strip()
        self._tmp_dir = Path(tmp_dir)
        self._timeout = int(timeout)
        self._exe: str | None = None
        self._info: dict | None = None

    # ------ 探测 ------ #
    def exe(self) -> str:
        """找到 tesseract.exe：优先用设置里的路径，其次 PATH。"""

        if self._exe:
            return self._exe
        configured = Path(self._configured_path)
        if self._configured_path and configured.exists():
            self._exe = str(configured)
        else:
            found = shutil.which("tesseract")
            if not found:
                raise AppError(
                    "TESSERACT_MISSING",
                    "没有找到 Tesseract",
                    "请安装 Tesseract 5.x（含 chi_sim 语言包），再在设置里指定 tesseract.exe",
                )
            self._exe = found
        return self._exe

    def _run(self, args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
        """执行 tesseract 命令；统一隐藏窗口并捕获输出。"""

        command = [self.exe(), *args]
        try:
            return subprocess.run(
                command,
                capture_output=True,
                timeout=timeout or self._timeout,
                creationflags=const.CREATE_NO_WINDOW,
            )
        except subprocess.TimeoutExpired as error:
            raise AppError(
                "TESSERACT_TIMEOUT",
                "Tesseract 识别超时",
                f"超过 {timeout or self._timeout} 秒",
            ) from error
        except OSError as error:
            raise AppError(
                "TESSERACT_FAILED", "无法启动 Tesseract", str(error)
            ) from error

    def prepare(self) -> dict:
        """读取版本与语言列表并缓存；重复调用只探测一次。"""

        if self._info is not None:
            return self._info

        version_result = self._run(["--version"], timeout=const.OCR_VERSION_TIMEOUT)
        version_text = version_result.stdout.decode("utf-8", "replace").strip()
        version = version_text.splitlines()[0] if version_text else "unknown"

        lang_result = self._run(["--list-langs"], timeout=const.OCR_LANGS_TIMEOUT)
        if lang_result.returncode != 0:
            raise AppError(
                "TESSERACT_FAILED",
                "无法读取 Tesseract 语言包列表",
                lang_result.stderr.decode("utf-8", "replace").strip(),
            )
        langs = _parse_langs(lang_result.stdout.decode("utf-8", "replace"))
        self._info = {"path": self.exe(), "version": version, "langs": langs}
        return self._info

    def ensure_lang(self, lang: str) -> None:
        """检查请求的语言包是否已安装；chi_sim+eng 会拆开逐个检查。"""

        info = self.prepare()
        available = set(info["langs"])
        missing = [name for name in lang.split("+") if name and name not in available]
        if missing:
            raise AppError(
                "TESSERACT_LANG_MISSING",
                f"Tesseract 缺少语言包：{', '.join(missing)}",
                "请安装 chi_sim（简体中文）后重试",
            )

    # ------ 识别 ------ #
    def text(
        self, image: Image.Image, lang: str | None = None, config: str | None = None
    ) -> str:
        """把 PIL 图片交给 tesseract，返回识别文本。"""

        use_lang = lang or const.DEFAULT_TUNING["ocr_lang"]
        use_config = config or const.DEFAULT_TUNING["ocr_config"]
        self.ensure_lang(use_lang)

        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp = self._tmp_dir / f"ocr-{uuid.uuid4().hex}.png"
        try:
            image.convert("RGB").save(tmp, format="PNG")
            args = [str(tmp), "stdout", "-l", use_lang, *use_config.split()]
            result = self._run(args)
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass

        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", "replace").strip()
            raise AppError(
                "TESSERACT_FAILED",
                "Tesseract 识别失败",
                detail[-const.OCR_ERROR_DETAIL_LIMIT:],
            )
        return result.stdout.decode("utf-8", "replace")


def _parse_langs(output: str) -> list[str]:
    """从 `tesseract --list-langs` 的输出里挑出语言代码。"""

    langs: list[str] = []
    for line in output.splitlines():
        name = line.strip()
        if not name or name.endswith(":") or " " in name:
            continue
        # 语言代码只含小写字母、数字、下划线
        if all(char.isalnum() or char == "_" for char in name):
            langs.append(name)
    return langs
