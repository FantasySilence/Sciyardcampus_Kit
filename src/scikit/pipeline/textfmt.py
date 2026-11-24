# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: OCR 文本整理：分段、公式标记、标签解析（纯函数）        #
# ================================================================== #
# 这一段不读写磁盘、不依赖 OCR 引擎，是最适合单测的部分。
# 规则与上游 TextExtraction 保持一致：
#   - 题干、每个选项、每个小问各成一段，段间空一行；
#   - 公式片段用 $...$ 包起来；
#   - 文件名后缀决定标签（_formula / _table / _image）。

from __future__ import annotations

import re

from scikit import const
from scikit.pipeline.defaults import Tuning

# 正则本体在 const.py，这里只编译一次
OPTION = re.compile(const.TEXT_OPTION_PATTERN)
SUB_ITEM = re.compile(const.TEXT_SUB_ITEM_PATTERN)
MATH = re.compile(const.TEXT_MATH_PATTERN)



def paragraphs(text: str) -> list[str]:
    """
    把 OCR 出来的行整理成“题干 / 每个选项 / 每个小问”各一段。

    换行截断的续行会接回上一段；整行都是公式的行单独成段，
    免得把公式和乱码粘成一大段。
    """

    result: list[str] = []
    for line in (row.strip() for row in text.splitlines()):
        if not line:
            continue
        if (
            not result
            or OPTION.match(line)
            or SUB_ITEM.match(line)
            or is_math_line(line)
        ):
            result.append(line)
        else:
            result[-1] = merge(result[-1], line)
    return result


def is_math_line(line: str) -> bool:
    """这一行是不是几乎只有英文数字（公式行），这种行不往上一段里并。"""

    chars = [char for char in line if not char.isspace()]
    if not chars:
        return False
    if (
        sum(1 for char in chars if char.isalnum())
        < const.TEXT_LINE_ALNUM_MIN
    ):
        return False
    return (
        sum(1 for char in chars if char.isascii()) / len(chars)
        >= const.TEXT_LINE_ASCII_RATIO
    )


def merge(previous: str, line: str) -> str:
    """拼接续行：中文直接接上，两侧都是英文/数字时补一个空格。"""

    if (
        previous
        and line
        and previous[-1].isascii()
        and previous[-1].isalnum()
        and line[0].isascii()
        and line[0].isalnum()
    ):
        return previous + " " + line
    return previous + line


def is_formula(run: str) -> bool:
    """判断一段英文数字是不是公式：有等号/上下标，或字母数字连写。"""

    run = run.strip()
    if len(run) < const.TEXT_FORMULA_MIN_LENGTH or not any(
        char.isalnum() for char in run
    ):
        return False
    if any(operator in run for operator in const.TEXT_FORMULA_OPERATORS):
        return True
    return (
        re.search(const.TEXT_FORMULA_DIGIT_LETTER_PATTERN, run) is not None
    )


def mark_math(paragraph: str) -> tuple[str, bool]:
    """
    把段落里的公式片段包成 $...$，返回 (处理后的段落, 是否含公式)。

    从右往左替换，避免改动前面片段的下标。
    """

    found = False
    for match in reversed(list(MATH.finditer(paragraph))):
        formula = match.group(0).strip()

        # 结尾的标点留在公式外面
        tail = ""
        while formula and formula[-1] in const.TEXT_TRAILING_PUNCT:
            tail = formula[-1] + tail
            formula = formula[:-1]

        # 夹着整词（Dale、HRSA）的多半是识别乱码，不当公式
        if not is_formula(formula) or re.search(
            const.TEXT_FORMULA_WORD_PATTERN, formula
        ):
            continue

        # 去掉多余空白，符号换成 LaTeX
        formula = re.sub(r"\s+", " ", formula)
        for symbol, latex in const.MATH_SYMBOLS.items():
            formula = formula.replace(symbol, latex)
        formula = re.sub(r"\s*([=+*/^_])\s*", r"\1", formula)
        formula = re.sub(r"\s*-\s*", "-", formula)

        paragraph = (
            paragraph[: match.start()] + "$" + formula + "$" + tail + paragraph[match.end() :]
        )
        found = True
    return paragraph, found


def kinds_of(name: str, tuning: Tuning) -> list[str]:
    """按文件名反推特征：1_formula_table.txt -> ['formula', 'table']。"""

    return [
        kind for kind in tuning.ocr_kind_order if tuning.ocr_kind_suffix[kind] in name
    ]
