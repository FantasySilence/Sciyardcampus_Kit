# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: OCR 文本整理（纯函数）测试                             #
# ================================================================== #

from __future__ import annotations

from scikit.pipeline import textfmt
from scikit.pipeline.defaults import Tuning


def test_paragraphs_merges_continuation_and_keeps_options() -> None:
    text = "题干第一行\n接着写\nA 选项一\nB 选项二\n（1）小问"
    result = textfmt.paragraphs(text)
    assert result[0] == "题干第一行接着写"
    assert result[1] == "A 选项一"
    assert result[2] == "B 选项二"
    assert result[3] == "（1）小问"


def test_merge_adds_space_between_ascii_words() -> None:
    assert textfmt.merge("abc", "def") == "abc def"
    assert textfmt.merge("中文", "续行") == "中文续行"


def test_mark_math_wraps_formula_and_keeps_punctuation() -> None:
    paragraph = "某商品需求为D=10-P，供给为S=2+P。"
    marked, found = textfmt.mark_math(paragraph)
    assert found is True
    assert "$D=10-P$" in marked
    assert "$S=2+P$" in marked


def test_mark_math_skips_plain_chinese() -> None:
    marked, found = textfmt.mark_math("这是一段普通的中文题干，没有公式。")
    assert found is False
    assert marked == "这是一段普通的中文题干，没有公式。"


def test_kinds_of_reads_suffixes_in_fixed_order() -> None:
    tuning = Tuning()
    assert textfmt.kinds_of("1_formula_table.txt", tuning) == ["formula", "table"]
    assert textfmt.kinds_of("1_image.txt", tuning) == ["image"]
    assert textfmt.kinds_of("1.txt", tuning) == []
