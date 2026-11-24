# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: OCR 流水线：题图 -> txt + 公式/表格/图像标签            #
# ================================================================== #
# 规则与上游 TextExtraction 一致：
#   纯文字         -> N.txt
#   含公式         -> N_formula.txt
#   含表格         -> N_table.txt
#   含图像/图形    -> N_image.txt
#   同时多个特征   -> 按 formula -> table -> image 拼接
# 单题失败不会中断整批：记录 ocrError，继续下一题；Tesseract 本身
# 缺失/语言包缺失属于致命错误，直接停下让用户先修环境。

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from PIL import Image

from scikit import const
from scikit.errors import AppError
from scikit.jobs import Reporter
from scikit.pipeline import textfmt
from scikit.pipeline.artifact_paths import ArtifactPaths
from scikit.pipeline.defaults import Tuning
from scikit.pipeline.ocr import OcrClient
from scikit.pipeline.shapes import QuestionShape


def write_one(
    png_path: Path,
    txt_dir: Path,
    index: int,
    ocr: OcrClient,
    tuning: Tuning,
) -> tuple[list[str], Path]:
    """
    识别一张题图并写成 txt，返回 (特征标签, txt 路径)。

    同时会把这道题以前生成的其它命名后缀清掉，避免 1.txt 与
    1_formula.txt 并存导致 Word 重复收录。
    """

    image = Image.open(png_path).convert("RGB")

    # 表格/图像看版面，用原始尺寸判断（阈值按 1600 宽标定）
    shapes = QuestionShape.kinds(image, tuning)

    if tuning.ocr_scale != 1:
        image = image.resize(
            (image.size[0] * tuning.ocr_scale, image.size[1] * tuning.ocr_scale),
            Image.LANCZOS,
        )

    text = ocr.text(image, lang=tuning.ocr_lang, config=tuning.ocr_config)

    has_math = False
    paragraphs: list[str] = []
    for paragraph in textfmt.paragraphs(text):
        line, found = textfmt.mark_math(paragraph) if tuning.ocr_mark_math else (paragraph, False)
        has_math = has_math or found
        paragraphs.append(line)

    kinds = (["formula"] if has_math else []) + shapes
    suffix = "".join(
        tuning.ocr_kind_suffix[kind]
        for kind in tuning.ocr_kind_order
        if kind in kinds
    )

    txt_dir.mkdir(parents=True, exist_ok=True)
    name = f"{int(index)}{suffix}{const.TXT_SUFFIX}"
    target = txt_dir / name
    with open(target, "w", encoding="utf-8") as file:
        file.write("\n\n".join(paragraphs) + "\n")

    # 清掉这道题以前的其它后缀，避免新旧文件名并存；
    # 通配符只匹配“<题号>_”，不能写成 “<题号>*”，否则 1 会误删 12.txt
    old_files = list(txt_dir.glob(f"{int(index)}_*{const.TXT_SUFFIX}"))
    old_files.append(txt_dir / f"{int(index)}{const.TXT_SUFFIX}")
    for old in old_files:
        if old.name != name:
            try:
                old.unlink()
            except OSError:
                pass

    return kinds, target


def extract_items(
    paths: ArtifactPaths,
    scope: dict,
    items: list[dict],
    ocr: OcrClient,
    reporter: Reporter,
    tuning: Tuning,
    *,
    indexes: Iterable[int] | None = None,
) -> dict:
    """
    对 items 批量 OCR，原地更新 tags/txt/ocrError，返回统计。

    scope: {"mode": "paper"|"type", "paper": ..., "pngType": ...}
    indexes: 只识别指定题号；None 表示全部
    """

    selected = set(int(value) for value in (indexes or []))
    targets = [
        item
        for item in items
        if not selected or int(item.get("index", 0)) in selected
    ]
    total = len(targets)
    if total == 0:
        reporter.log("没有需要识别的题目", "warn")
        return {"total": 0, "ok": 0, "failed": 0, "tags": {"formula": 0, "table": 0, "image": 0}}

    txt_dir = (
        paths.paper_txt_dir(scope["paper"])
        if scope.get("mode") == "paper"
        else paths.type_txt_dir(scope["pngType"])
    )

    ok = 0
    failed = 0
    tag_counts = {"formula": 0, "table": 0, "image": 0}
    reporter.progress(0, total, "准备识别", "ocr")

    for position, item in enumerate(targets, start=1):
        reporter.check()
        index = int(item["index"])
        label = f"第{index}题"
        reporter.progress(position - 1, total, f"识别 {label}", "ocr")

        png_path = paths.root / item["png"]
        if not png_path.exists():
            failed += 1
            item["ocrError"] = "题图不存在"
            reporter.log(f"{label}：题图不存在，跳过", "error")
            continue

        try:
            tags, target = write_one(png_path, txt_dir, index, ocr, tuning)
        except AppError as error:
            if error.code in const.FATAL_OCR_CODES:
                raise
            failed += 1
            item["ocrError"] = error.message
            reporter.log(f"{label}：识别失败（{error.message}）", "error")
            continue
        except Exception as error:  # noqa: BLE001 - 单题失败不拖垮整批
            failed += 1
            item["ocrError"] = f"{type(error).__name__}: {error}"
            reporter.log(f"{label}：识别异常（{error}）", "error")
            continue

        ok += 1
        item["tags"] = tags
        item["txt"] = paths.rel(target)
        item["ocrError"] = ""
        for kind in tags:
            if kind in tag_counts:
                tag_counts[kind] += 1

        note = "、".join(tuning.kind_labels[kind] for kind in tags)
        reporter.log(
            f"已保存 {scope_name(scope)}/{target.name}" + (f"（{note}）" if note else ""),
            "success",
        )
        reporter.progress(position, total, f"已识别 {position}/{total}", "ocr")

    reporter.log(
        f"识别完成：成功 {ok} 题，失败 {failed} 题；"
        f"公式 {tag_counts['formula']}、表格 {tag_counts['table']}、图像 {tag_counts['image']}",
        "success" if failed == 0 else "warn",
    )
    return {"total": total, "ok": ok, "failed": failed, "tags": tag_counts}


def scope_name(scope: dict) -> str:
    """给日志用的范围名称。"""

    if scope.get("mode") == "paper":
        return str(scope.get("paper", ""))
    return str(scope.get("pngType", ""))
