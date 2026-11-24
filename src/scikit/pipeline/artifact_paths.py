# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 产物路径解析：resources 布局、卷名清洗、媒体路径校验    #
# ================================================================== #
# 与上游保持一致：
#   resources/row_pngs/<题型>/<题号>.png
#   resources/row_txt/<题型>/<题号>[_标签].txt
#   resources/row_paper/<卷名>/pngs|txts/
#   resources/word_output/<名字>.docx
# 应用私有文件全部放 <root>/.scikit/，不污染 resources。
# 数据根在源码运行时是仓库根，打包后是 exe 所在目录，可在设置里自定义。

from __future__ import annotations

import re
from pathlib import Path

from scikit import const
from scikit.errors import AppError


class ArtifactPaths:
    """一个数据根目录下的全部产物路径。"""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.resources_dir = self.root / const.RESOURCES_DIR_NAME
        self.row_pngs_dir = self.resources_dir / const.ROW_PNGS_DIR_NAME
        self.row_txt_dir = self.resources_dir / const.ROW_TXT_DIR_NAME
        self.row_paper_dir = self.resources_dir / const.ROW_PAPER_DIR_NAME
        self.word_output_dir = self.resources_dir / const.WORD_OUTPUT_DIR_NAME

        # 应用私有目录：设置、会话、探针图、缩略图、OCR 临时图
        self.scikit_dir = self.root / const.SCIKIT_DIR_NAME
        self.settings_dir = self.scikit_dir / const.SETTINGS_SUBDIR
        self.sessions_dir = self.scikit_dir / const.SESSIONS_SUBDIR
        self.probe_dir = self.scikit_dir / const.PROBE_SUBDIR
        self.thumbs_dir = self.scikit_dir / const.THUMBS_SUBDIR
        self.tmp_dir = self.scikit_dir / const.TMP_SUBDIR
        self.webview_dir = self.scikit_dir / const.WEBVIEW_CACHE_DIR_NAME

    # ------ 目录 ------ #
    def ensure(self) -> None:
        """创建所有需要的目录（幂等）。"""

        for folder in (
            self.row_pngs_dir,
            self.row_txt_dir,
            self.row_paper_dir,
            self.word_output_dir,
            self.settings_dir,
            self.sessions_dir,
            self.probe_dir,
            self.thumbs_dir,
            self.tmp_dir,
            self.webview_dir,
        ):
            folder.mkdir(parents=True, exist_ok=True)

    def type_dir(self, png_type: str) -> Path:
        """分题型的图片目录：resources/row_pngs/<题型>/。"""

        folder = self.row_pngs_dir / self.safe_name(png_type, "题型")
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def type_txt_dir(self, png_type: str) -> Path:
        """分题型的文字目录：resources/row_txt/<题型>/。"""

        folder = self.row_txt_dir / self.safe_name(png_type, "题型")
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def paper_dir(self, paper: str) -> Path:
        """整卷目录：resources/row_paper/<卷名>/。"""

        folder = self.row_paper_dir / self.safe_name(paper, "卷名")
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def paper_png_dir(self, paper: str) -> Path:
        """整卷图片目录：resources/row_paper/<卷名>/pngs/。"""

        folder = self.paper_dir(paper) / const.PAPER_PNGS_SUBDIR
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def paper_txt_dir(self, paper: str) -> Path:
        """整卷文字目录：resources/row_paper/<卷名>/txts/。"""

        folder = self.paper_dir(paper) / const.PAPER_TXTS_SUBDIR
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    # ------ 文件 ------ #
    def png_path(self, png_type: str, index: int) -> Path:
        """分题型题图：row_pngs/<题型>/<题号>.png。"""

        return self.type_dir(png_type) / f"{int(index)}{const.PNG_SUFFIX}"

    def txt_path(self, png_type: str, index: int, suffix: str = "") -> Path:
        """分题型 txt：row_txt/<题型>/<题号><后缀>.txt。"""

        return self.type_txt_dir(png_type) / f"{int(index)}{suffix}{const.TXT_SUFFIX}"

    def paper_png_path(self, paper: str, index: int) -> Path:
        """整卷题图：row_paper/<卷名>/pngs/<顺序号>.png。"""

        return self.paper_png_dir(paper) / f"{int(index)}{const.PNG_SUFFIX}"

    def paper_txt_path(self, paper: str, index: int, suffix: str = "") -> Path:
        """整卷 txt：row_paper/<卷名>/txts/<顺序号><后缀>.txt。"""

        return self.paper_txt_dir(paper) / f"{int(index)}{suffix}{const.TXT_SUFFIX}"

    def word_path(self, filename: str) -> Path:
        """Word 输出路径；只接受文件名，自动补 .docx。"""

        name = self.safe_filename(filename)
        if not name.lower().endswith(const.DOCX_SUFFIX):
            name += const.DOCX_SUFFIX
        self.word_output_dir.mkdir(parents=True, exist_ok=True)
        return self.word_output_dir / name

    # ------ 相对路径 / 媒体 ------ #
    def rel(self, path: str | Path) -> str:
        """把绝对路径转成相对数据根的 POSIX 路径；不在根内返回空串。"""

        try:
            return Path(path).resolve().relative_to(self.root).as_posix()
        except (ValueError, OSError):
            return ""

    def resolve_rel(self, relative: str) -> Path:
        """
        把前端传来的相对路径还原成绝对路径，并做目录包含检查。

        只允许 resources/ 与 .scikit/probe/ 下的内容，防止 ../ 读到用户其它文件。
        """

        if not relative or "\x00" in relative:
            raise AppError("INVALID_PATH", "路径无效")
        # 统一分隔符，拒绝绝对路径和盘符
        cleaned = relative.replace("\\", "/").lstrip("/")
        candidate = (self.root / cleaned).resolve()
        allowed = (
            self._is_under(candidate, self.resources_dir)
            or self._is_under(candidate, self.probe_dir)
        )
        if not allowed:
            raise AppError("INVALID_PATH", "不允许访问该路径", relative)
        return candidate

    def media_url_path(self, path: str | Path) -> str:
        """给前端用的相对路径；不是媒体文件时返回空串。"""

        candidate = Path(path)
        if candidate.suffix.lower() not in const.IMAGE_SUFFIXES:
            return ""
        return self.rel(candidate)

    @staticmethod
    def _is_under(path: Path, parent: Path) -> bool:
        """判断 path 是否在 parent 目录内（含相等）。"""

        try:
            path.relative_to(parent.resolve())
            return True
        except ValueError:
            return False

    # ------ 名称清洗 ------ #
    @staticmethod
    def safe_name(value: str, label: str) -> str:
        """
        清洗卷名/题型名：拒绝路径分隔符、Windows 非法字符、保留设备名。

        这里宁可报错让用户改名，也不静默替换，免得产物落到意外的目录。
        """

        name = str(value or "").strip().rstrip(". ")
        if not name:
            raise AppError("INVALID_NAME", f"{label}不能为空")
        if name in (".", ".."):
            raise AppError("INVALID_NAME", f"{label}不能是 . 或 ..")
        bad = sorted(
            {char for char in name if char in const.INVALID_CHARS or ord(char) < 32}
        )
        if bad:
            raise AppError(
                "INVALID_NAME",
                f"{label}含有非法字符：{' '.join(repr(char) for char in bad)}",
                "请不要使用 \\ / : * ? \" < > |",
            )
        if name.upper() in const.RESERVED_NAMES:
            raise AppError("INVALID_NAME", f"{label}不能使用系统保留名：{name}")
        if len(name) > const.MAX_NAME_LENGTH:
            raise AppError(
                "INVALID_NAME", f"{label}太长（最多 {const.MAX_NAME_LENGTH} 字）"
            )
        return name

    @staticmethod
    def safe_filename(value: str) -> str:
        """清洗输出文件名：只取文件名部分，去非法字符，保留 .docx。"""

        name = Path(str(value or "").strip()).name.rstrip(". ")
        if not name:
            raise AppError("INVALID_NAME", "文件名不能为空")
        bad = sorted(
            {char for char in name if char in const.INVALID_CHARS or ord(char) < 32}
        )
        if bad:
            raise AppError("INVALID_NAME", "文件名含有非法字符", "".join(bad))
        if len(name) > const.MAX_FILENAME_LENGTH:
            raise AppError(
                "INVALID_NAME",
                f"文件名太长（最多 {const.MAX_FILENAME_LENGTH} 字）",
            )
        return name

    # ------ 扫描 ------ #
    def list_types(self) -> list[str]:
        """row_pngs 下已有的题型目录名（排序）。"""

        if not self.row_pngs_dir.exists():
            return []
        return sorted(
            item.name for item in self.row_pngs_dir.iterdir() if item.is_dir()
        )

    def list_papers(self) -> list[str]:
        """row_paper 下已有的卷名（排序）。"""

        if not self.row_paper_dir.exists():
            return []
        return sorted(
            item.name for item in self.row_paper_dir.iterdir() if item.is_dir()
        )

    def count_pngs(self, folder: Path) -> int:
        """数一个目录下有多少张 png。"""

        if not folder.is_dir():
            return 0
        return len(
            [item for item in folder.iterdir() if item.suffix.lower() == ".png"]
        )

    def numeric_index(self, name: str) -> int:
        """从文件名里取题号/顺序号；取不到返回 -1。"""

        match = re.match(r"^(\d+)", name)
        return int(match.group(1)) if match else -1
