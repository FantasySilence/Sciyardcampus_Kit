# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 产物扫描：题型/整卷清单、从磁盘合成会话、历史列表       #
# ================================================================== #
# 上游 Status 是“打印报表”；这里改成结构化 JSON，供历史面板和预览页使用。
# 旧产物没有 session 时，用 build_items_from_files 合成只读条目。

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from scikit import const
from scikit.pipeline.artifact_paths import ArtifactPaths
from scikit.pipeline.defaults import Tuning
from scikit.pipeline.textfmt import kinds_of


def scope_title(scope: dict) -> str:
    """范围标题：整卷用卷名，单题型用题型名。"""

    if scope.get("mode") == "paper":
        return str(scope.get("paper", const.DEFAULT_PAPER_TITLE))
    return str(scope.get("pngType", const.DEFAULT_TYPE_TITLE))


def scope_key(scope: dict) -> str:
    """范围唯一键，用于判断文件产物是否已有 session。"""

    if scope.get("mode") == "paper":
        return f"paper:{scope.get('paper', '')}"
    return f"type:{scope.get('pngType', '')}"


def find_txt(paths: ArtifactPaths, scope: dict, index: int) -> Path | None:
    """找一道题对应的 txt：优先带标签的，其次纯文字。"""

    folder = (
        paths.paper_txt_dir(scope["paper"])
        if scope.get("mode") == "paper"
        else paths.type_txt_dir(scope["pngType"])
    )
    tagged = sorted(folder.glob(f"{int(index)}_*{const.TXT_SUFFIX}"))
    if tagged:
        return tagged[0]
    plain = folder / f"{int(index)}{const.TXT_SUFFIX}"
    return plain if plain.exists() else None


def read_item_text(paths: ArtifactPaths, item: dict) -> str:
    """读取会话条目的 OCR 文字；文件缺失时返回空串。"""

    relative = item.get("txt") or ""
    if not relative:
        return ""
    path = paths.root / relative
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def build_items_from_files(
    paths: ArtifactPaths,
    scope: dict,
    tuning: Tuning,
    *,
    saved: dict | None = None,
) -> list[dict]:
    """
    扫描磁盘合成条目列表（旧产物、历史预览用）。

    saved: 同范围的 session；有的话优先沿用其中的 kind/included/ocrError，
           这样用户在预览页剔除的题，重新打开历史仍然保持剔除。
    """

    if scope.get("mode") == "paper":
        png_dir = paths.paper_png_dir(scope["paper"])
        kind_default = "未知"
    else:
        png_dir = paths.type_dir(scope["pngType"])
        kind_default = scope["pngType"]

    saved_by_index = {
        int(item["index"]): item for item in (saved or {}).get("items", [])
    }

    items: list[dict] = []
    for png in sorted(
        png_dir.glob(f"*{const.PNG_SUFFIX}"),
        key=lambda item: paths.numeric_index(item.name),
    ):
        index = paths.numeric_index(png.name)
        if index <= 0:
            continue
        txt = find_txt(paths, scope, index)
        tags = kinds_of(txt.name, tuning) if txt is not None else []
        previous = saved_by_index.get(index, {})
        items.append(
            {
                "index": index,
                "number": previous.get("number", index),
                "kind": previous.get("kind", kind_default),
                "png": paths.rel(png),
                "txt": paths.rel(txt) if txt is not None else "",
                "tags": previous.get("tags", tags),
                "included": bool(previous.get("included", True)),
                "exportMode": previous.get(
                    "exportMode", const.DEFAULT_EXPORT_MODE
                ),
                "ocrError": previous.get("ocrError", ""),
            }
        )
    return items


def effective_mode(item: dict) -> str:
    """
    这道题在 Word 里实际用文字还是图片。

    auto：有公式/表格/图像标签就贴图，否则转文字（与上游一致）；
    text / image：用户在预览里显式指定。
    """

    mode = str(item.get("exportMode") or const.DEFAULT_EXPORT_MODE)
    if mode in ("text", "image"):
        return mode
    return "image" if item.get("tags") else "text"


def count_tags(paths: ArtifactPaths, txt_dir: Path, tuning: Tuning) -> dict:
    """统计一个 txt 目录里带公式/表格/图像的题数。"""

    counts = {kind: 0 for kind in tuning.ocr_kind_order}
    if not txt_dir.is_dir():
        return counts
    for file in txt_dir.iterdir():
        if file.suffix.lower() != const.TXT_SUFFIX:
            continue
        for kind in kinds_of(file.name, tuning):
            counts[kind] += 1
    return counts


def inventory(paths: ArtifactPaths, tuning: Tuning) -> dict:
    """扫描 resources，返回题型与整卷的结构化清单。"""

    types = []
    for name in paths.list_types():
        png_dir = paths.row_pngs_dir / name
        txt_dir = paths.row_txt_dir / name
        txts = (
            list(txt_dir.glob(f"*{const.TXT_SUFFIX}"))
            if txt_dir.is_dir()
            else []
        )
        docx = (
            paths.word_output_dir
            / f"{name}{tuning.word_title_suffix}{const.DOCX_SUFFIX}"
        )
        types.append(
            {
                "name": name,
                "pngs": paths.count_pngs(png_dir),
                "txts": len(txts),
                "tags": count_tags(paths, txt_dir, tuning),
                "docx": docx.name if docx.exists() else "",
                "updatedAt": _mtime(png_dir),
            }
        )

    papers = []
    for name in paths.list_papers():
        png_dir = paths.paper_png_dir(name)
        txt_dir = paths.paper_txt_dir(name)
        txts = (
            list(txt_dir.glob(f"*{const.TXT_SUFFIX}"))
            if txt_dir.is_dir()
            else []
        )
        docx = paths.word_output_dir / f"{name}{const.DOCX_SUFFIX}"
        papers.append(
            {
                "name": name,
                "pngs": paths.count_pngs(png_dir),
                "txts": len(txts),
                "tags": count_tags(paths, txt_dir, tuning),
                "docx": docx.name if docx.exists() else "",
                "updatedAt": _mtime(png_dir),
            }
        )

    return {"types": types, "papers": papers}


def history(paths: ArtifactPaths, tuning: Tuning, sessions: Iterable[dict]) -> list[dict]:
    """
    合并“已保存 session”和“只有文件”的历史条目。

    返回 [{id, title, scope, source, total, included, updatedAt, docx, docxExists}]
    """

    entries: list[dict] = []
    covered: set[str] = set()
    for session in sessions:
        scope = session.get("scope", {})
        covered.add(scope_key(scope))
        stats = session.get("stats", {})
        entries.append(
            {
                "id": session.get("id", ""),
                "title": scope_title(scope),
                "scope": scope,
                "source": session.get("source", "capture"),
                "total": int(stats.get("total", 0)),
                "included": int(stats.get("included", 0)),
                "updatedAt": session.get("updatedAt", ""),
                "docx": _docx_name(paths, scope, tuning),
                "docxExists": _docx_exists(paths, scope, tuning),
            }
        )

    # 文件里有、但没有任何 session 的范围，补成只读历史项
    for name in paths.list_types():
        scope = {"mode": "type", "pngType": name}
        if scope_key(scope) in covered:
            continue
        pngs = paths.count_pngs(paths.row_pngs_dir / name)
        if pngs == 0:
            continue
        entries.append(
            {
                "id": "",
                "title": name,
                "scope": scope,
                "source": "files",
                "total": pngs,
                "included": pngs,
                "updatedAt": _mtime(paths.row_pngs_dir / name),
                "docx": _docx_name(paths, scope, tuning),
                "docxExists": _docx_exists(paths, scope, tuning),
            }
        )
    for name in paths.list_papers():
        scope = {"mode": "paper", "paper": name}
        if scope_key(scope) in covered:
            continue
        pngs = paths.count_pngs(paths.paper_png_dir(name))
        if pngs == 0:
            continue
        entries.append(
            {
                "id": "",
                "title": name,
                "scope": scope,
                "source": "files",
                "total": pngs,
                "included": pngs,
                "updatedAt": _mtime(paths.paper_png_dir(name)),
                "docx": _docx_name(paths, scope, tuning),
                "docxExists": _docx_exists(paths, scope, tuning),
            }
        )

    entries.sort(key=lambda item: item.get("updatedAt", ""), reverse=True)
    return entries


def stats_for_items(items: Iterable[dict], tuning: Tuning) -> dict:
    """统计条目：总数、勾选数、三类标签数、被剔除数。"""

    items = list(items)
    tags = {kind: 0 for kind in tuning.ocr_kind_order}
    included = 0
    text_count = 0
    image_count = 0
    for item in items:
        if item.get("included", True):
            included += 1
            if effective_mode(item) == "image":
                image_count += 1
            else:
                text_count += 1
        for kind in item.get("tags", []):
            if kind in tags:
                tags[kind] += 1
    return {
        "total": len(items),
        "included": included,
        "excluded": len(items) - included,
        "formula": tags["formula"],
        "table": tags["table"],
        "image": tags["image"],
        "textCount": text_count,
        "imageCount": image_count,
    }


def _mtime(folder: Path) -> str:
    """目录最后修改时间（ISO 字符串）；不存在返回空串。"""

    try:
        return datetime.fromtimestamp(folder.stat().st_mtime).isoformat(timespec="seconds")
    except OSError:
        return ""


def _docx_name(paths: ArtifactPaths, scope: dict, tuning: Tuning) -> str:
    """这个范围对应的 Word 文件名。"""

    if scope.get("mode") == "paper":
        return f"{scope.get('paper', '')}{const.DOCX_SUFFIX}"
    return (
        f"{scope.get('pngType', '')}{tuning.word_title_suffix}"
        f"{const.DOCX_SUFFIX}"
    )


def _docx_exists(paths: ArtifactPaths, scope: dict, tuning: Tuning) -> bool:
    """这个范围的 Word 是否已存在。"""

    try:
        return (paths.word_output_dir / _docx_name(paths, scope, tuning)).exists()
    except OSError:
        return False
