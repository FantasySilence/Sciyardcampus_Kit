# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: Word 导出测试：文字题、贴图题、剔除过滤                 #
# ================================================================== #

from __future__ import annotations

from docx import Document

from scikit.jobs import Job, Reporter
from scikit.pipeline import docx
from scikit.pipeline.defaults import Tuning


def make_items(data_root, numbers: tuple[int, ...]) -> list[dict]:
    items = []
    for number in numbers:
        items.append(
            {
                "index": number,
                "number": number,
                "kind": "选择题",
                "png": data_root.rel(data_root.png_path("选择题", number)),
                "txt": data_root.rel(data_root.txt_path("选择题", number)),
                "tags": [],
                "included": True,
                "ocrError": "",
            }
        )
    return items


def write_texts(data_root, numbers: tuple[int, ...]) -> None:
    for number in numbers:
        data_root.txt_path("选择题", number).write_text(
            f"第{number}题的题干。\n\nA 选项\n\nB 选项\n", encoding="utf-8"
        )


def build_report() -> Reporter:
    return Reporter(Job(id="test", kind="export", title="export", payload={}))


def test_build_text_questions(data_root, seed_cards, tuning: Tuning) -> None:
    numbers = tuple(seed_cards())
    write_texts(data_root, numbers)
    items = make_items(data_root, numbers)

    result = docx.build(
        data_root,
        {"mode": "type", "pngType": "选择题"},
        items,
        "选择题题库.docx",
        tuning,
        build_report(),
    )

    assert result["textCount"] == 3
    assert result["imageCount"] == 0
    target = data_root.word_output_dir / "选择题题库.docx"
    assert target.exists()
    assert len(Document(target).paragraphs) > 0


def test_tagged_question_is_embedded_as_image(data_root, seed_cards, tuning: Tuning) -> None:
    numbers = tuple(seed_cards())
    write_texts(data_root, numbers)
    items = make_items(data_root, numbers)
    items[1]["tags"] = ["formula"]
    # 有标签时 Word 里贴原图，不再读纯文字
    data_root.txt_path("选择题", 274, "_formula").write_text("公式题", encoding="utf-8")

    result = docx.build(
        data_root,
        {"mode": "type", "pngType": "选择题"},
        items,
        "选择题题库.docx",
        tuning,
        build_report(),
    )

    assert result["imageCount"] == 1
    assert result["textCount"] == 2


def test_explicit_text_mode_wins_over_tags(data_root, seed_cards, tuning: Tuning) -> None:
    numbers = tuple(seed_cards())
    write_texts(data_root, numbers)
    items = make_items(data_root, numbers)
    items[1]["tags"] = ["formula"]
    items[1]["exportMode"] = "text"

    result = docx.build(
        data_root,
        {"mode": "type", "pngType": "选择题"},
        items,
        "选择题题库.docx",
        tuning,
        build_report(),
    )

    assert result["textCount"] == 3
    assert result["imageCount"] == 0


def test_explicit_image_mode_for_plain_question(data_root, seed_cards, tuning: Tuning) -> None:
    numbers = tuple(seed_cards())
    write_texts(data_root, numbers)
    items = make_items(data_root, numbers)
    items[0]["exportMode"] = "image"

    result = docx.build(
        data_root,
        {"mode": "type", "pngType": "选择题"},
        items,
        "选择题题库.docx",
        tuning,
        build_report(),
    )

    assert result["imageCount"] == 1
    assert result["textCount"] == 2


def test_excluded_questions_are_skipped(data_root, seed_cards, tuning: Tuning) -> None:
    numbers = tuple(seed_cards())
    write_texts(data_root, numbers)
    items = make_items(data_root, numbers)
    items[0]["included"] = False

    result = docx.build(
        data_root,
        {"mode": "type", "pngType": "选择题"},
        items,
        "选择题题库.docx",
        tuning,
        build_report(),
    )

    assert result["total"] == 2
    assert result["textCount"] == 2
