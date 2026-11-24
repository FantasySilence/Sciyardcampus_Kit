# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: Word 导出：把预览里勾选的题合成题库文档                #
# ================================================================== #
# 规则与上游 WordBuilder / PaperWordBuilder 一致：
#   - 带 formula/table/image 标签的题：贴题目原图（等比铺满正文宽度）；
#   - 纯文字题：把 txt 里的段落转成正文；
#   - 每道题前写“第N题”（N 是题号/顺序号）。
# 差异：只处理会话里 included=True 的题，保证“预览所见 = 导出的内容”。

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from scikit import const
from scikit.errors import AppError
from scikit.jobs import Reporter
from scikit.pipeline.artifact_paths import ArtifactPaths
from scikit.pipeline.defaults import Tuning
from scikit.pipeline.library import effective_mode


def setup(document, tuning: Tuning) -> None:
    """页面和字体：A4、2.54 厘米页边距、宋体五号（可配置）。"""

    section = document.sections[0]
    section.page_width = Cm(const.WORD_PAGE_WIDTH_CM)
    section.page_height = Cm(const.WORD_PAGE_HEIGHT_CM)
    section.left_margin = Cm(const.WORD_PAGE_MARGIN_CM)
    section.right_margin = Cm(const.WORD_PAGE_MARGIN_CM)
    section.top_margin = Cm(const.WORD_PAGE_MARGIN_CM)
    section.bottom_margin = Cm(const.WORD_PAGE_MARGIN_CM)

    normal = document.styles["Normal"]
    normal.font.name = tuning.word_font
    normal.font.size = Pt(tuning.word_font_size)
    normal.element.get_or_add_rPr().get_or_add_rFonts().set(
        qn("w:eastAsia"), tuning.word_font
    )


def usable_width(document) -> int:
    """页面可用宽度（EMU）= 纸宽 - 左右边距。"""

    section = document.sections[0]
    return section.page_width - section.left_margin - section.right_margin


def add_title(document, index: int, tuning: Tuning) -> None:
    """每道题前面的小标题。"""

    try:
        text = tuning.word_question_title % index
    except (TypeError, ValueError):
        text = f"第{index}题"
    run = document.add_paragraph().add_run(text)
    run.bold = True


def add_text(document, txt_path: Path) -> None:
    """纯文字题：txt 里的每一段转成一个 Word 段落。"""

    with open(txt_path, encoding="utf-8") as file:
        paragraphs = [
            part.strip()
            for part in file.read().split(const.TXT_PARAGRAPH_SEPARATOR)
            if part.strip()
        ]
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)


def add_picture(document, png_path: Path) -> None:
    """带标签的题：贴题目原图，铺满正文宽度。"""

    document.add_picture(str(png_path), width=usable_width(document))
    document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def default_filename(scope: dict, tuning: Tuning) -> str:
    """默认输出文件名：整卷 <卷名>.docx，单题型 <题型>题库.docx。"""

    if scope.get("mode") == "paper":
        return (
            f"{scope.get('paper', const.WORD_DEFAULT_PAPER_NAME)}"
            f"{const.DOCX_SUFFIX}"
        )
    return (
        f"{scope.get('pngType', const.WORD_DEFAULT_TYPE_NAME)}"
        f"{tuning.word_title_suffix}{const.DOCX_SUFFIX}"
    )


def build(
    paths: ArtifactPaths,
    scope: dict,
    items: list[dict],
    filename: str,
    tuning: Tuning,
    reporter: Reporter,
    *,
    overwrite: bool = True,
) -> dict:
    """
    按 items 生成 Word，返回统计。

    filename: 只接受文件名，最终落在 resources/word_output/
    overwrite: False 时遇到同名文件直接报错（前端可二次确认后改 True）
    """

    included = [item for item in items if item.get("included", True)]
    if not included:
        raise AppError("NOTHING_TO_EXPORT", "没有勾选任何题目，无法导出")

    target = paths.word_path(filename)
    if target.exists() and not overwrite:
        raise AppError("FILE_EXISTS", "同名 Word 已存在", target.name)

    document = Document()
    setup(document, tuning)

    text_count = 0
    image_count = 0
    skipped: list[int] = []
    total = len(included)
    reporter.progress(0, total, "准备导出 Word", "export")

    for position, item in enumerate(included, start=1):
        reporter.check()
        index = int(item.get("index", position))
        reporter.progress(position - 1, total, f"写入第{index}题", "export")

        mode = effective_mode(item)
        png_path = paths.root / item["png"] if item.get("png") else None
        txt_path = paths.root / item["txt"] if item.get("txt") else None
        has_png = png_path is not None and png_path.exists()
        has_txt = txt_path is not None and txt_path.exists()

        # 用户选图片（或 auto 且带标签）：贴原图
        if mode == "image":
            if has_png:
                add_title(document, index, tuning)
                add_picture(document, png_path)
                image_count += 1
            elif has_txt:
                add_title(document, index, tuning)
                reporter.log(f"第{index}题选择图片但原图不存在，已退回文字", "warn")
                add_text(document, txt_path)
                text_count += 1
            else:
                skipped.append(index)
                reporter.log(f"第{index}题原图和 txt 都不存在，跳过", "error")
            continue

        # 用户选文字（或 auto 且无标签）：转正文
        if has_txt:
            add_title(document, index, tuning)
            add_text(document, txt_path)
            text_count += 1
        elif has_png:
            add_title(document, index, tuning)
            reporter.log(f"第{index}题选择文字但没有 txt，已退回图片", "warn")
            add_picture(document, png_path)
            image_count += 1
        else:
            skipped.append(index)
            reporter.log(f"第{index}题没有 txt，跳过", "warn")

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        document.save(str(target))
    except OSError as error:
        raise AppError("WRITE_FAILED", "无法写入 Word", str(error)) from error

    reporter.progress(total, total, "Word 已生成", "export")
    reporter.log(
        f"已保存 {target.name}（文字 {text_count} 题，图片 {image_count} 题，"
        f"跳过 {len(skipped)} 题）",
        "success",
    )
    return {
        "path": paths.rel(target),
        "name": target.name,
        "textCount": text_count,
        "imageCount": image_count,
        "skipped": skipped,
        "total": total,
    }
