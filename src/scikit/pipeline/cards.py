# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 从整屏画面里识别并裁出“一道题”（上游算法移植）          #
# ================================================================== #
# 识别依据（数苑试卷页面的固定样式）：
#   1. 标题行里有红色“（x分）”，用纯红像素定位每道题的起点；
#   2. 正文是深色字，页脚是浅灰字，靠亮度差把页脚摘出去；
#   3. 正文下面能读到页脚，说明这道题完整露出来了；
#   4. 两道题之间隔着下一题的标题行，所以本题下边界就是下一题标题行。

from __future__ import annotations

import re
from typing import NamedTuple

import numpy as np
from PIL import Image

from scikit import const
from scikit.pipeline.defaults import Tuning
from scikit.pipeline.ocr import OcrClient


class Card(NamedTuple):
    """一张题卡在整屏画面里占的行区间（单位是虚拟机像素）。"""

    header_top: int  # “题目N（x分）”标题行的上沿
    top: int  # 题干第一行文字的上沿
    bottom: int  # 最后一行选项文字的下沿
    footer: int  # 页脚那行灰字的上沿，-1 表示没看到

    def complete(self, tuning: Tuning) -> bool:
        """标题行、题干、页脚都在画面里，才算这道题完整。"""

        return (
            self.header_top > tuning.card_safe_top
            and self.top > tuning.card_safe_top
            and self.footer > 0
        )

    def cut_bottom(self, tuning: Tuning) -> bool:
        """题干看得见、页脚还没露出来，说明被画面下边缘切掉了。"""

        return self.top > tuning.card_safe_top and self.footer < 0

    def to_dict(self, number: int | None = None, kind: str | None = None) -> dict:
        """转成前端叠加框需要的数据（仍用虚拟机像素坐标）。"""

        return {
            "headerTop": self.header_top,
            "top": self.top,
            "bottom": self.bottom,
            "footer": self.footer,
            "number": number,
            "kind": kind or "",
        }


class QuestionCard:
    """从整屏画面里切出“一道题”，只保留题干和选项，不带标题与页脚。"""

    @staticmethod
    def runs(mask: np.ndarray) -> list[tuple[int, int]]:
        """把 True 的连续行合并成区间，隔 1 行以上才算断开。"""

        rows: list[tuple[int, int]] = []
        for index in (int(value) for value in np.nonzero(mask)[0]):
            if rows and index - rows[-1][1] <= 1:
                rows[-1] = (rows[-1][0], index)
            else:
                rows.append((index, index))
        return rows

    @staticmethod
    def split(frame: Image.Image, tuning: Tuning) -> list[Card]:
        """找出画面里每一道题的区间，按从上到下返回。"""

        array = np.asarray(frame.convert("RGB")).astype(int)
        height, width = array.shape[:2]
        lum = array.mean(axis=2)

        # 行号一律换算成虚拟机像素，和截图缩放无关
        scale = width / tuning.screen_width

        red = array[:, :, 0] > tuning.card_red[0]
        red &= array[:, :, 1] < tuning.card_red[1]
        red &= array[:, :, 2] < tuning.card_red[2]
        ink = lum < 200
        dark_rows = (lum < tuning.card_dark_lum).any(axis=1)

        # 页脚是浅灰字：这一行最暗的像素也够亮，才算页脚
        footer_area = ink[:, : tuning.card_footer_width]
        footer_min = np.where(
            footer_area, lum[:, : tuning.card_footer_width], 255.0
        ).min(axis=1)
        footer_rows = footer_area.any(axis=1) & (footer_min > tuning.card_footer_lum)

        footers = [
            (top, bottom)
            for top, bottom in QuestionCard.runs(footer_rows)
            if bottom - top >= tuning.card_footer_min
        ]

        # 红字只占“（x分）”几个字，补成它所在的那一整行标题
        ink_runs = QuestionCard.runs(ink.any(axis=1))
        headers: list[tuple[int, int]] = []
        for red_top, _ in QuestionCard.runs(red.any(axis=1)):
            for ink_top, ink_bottom in ink_runs:
                if ink_top <= red_top <= ink_bottom:
                    headers.append((ink_top, ink_bottom))
                    break

        cards: list[Card] = []
        for index, (header_top, header_bottom) in enumerate(headers):
            limit = headers[index + 1][0] if index + 1 < len(headers) else height
            body = np.nonzero(dark_rows[header_bottom + 1 : limit])[0]
            if len(body) == 0:
                continue
            bottom = header_bottom + 1 + int(body[-1])

            footer = -1
            for footer_top, _ in footers:
                if footer_top > bottom:
                    footer = footer_top
                    break

            cards.append(
                Card(
                    header_top=int(round(header_top / scale)),
                    top=int(round((header_bottom + 1 + int(body[0])) / scale)),
                    bottom=int(round(bottom / scale)),
                    footer=-1 if footer < 0 else int(round(footer / scale)),
                )
            )
        return cards

    @staticmethod
    def header_number(
        frame: Image.Image, card: Card, ocr: OcrClient, tuning: Tuning
    ) -> int | None:
        """
        从标题行读出题目编号（题目273 -> 273），读不出来返回 None。

        编号是截图的唯一键，所以只认“题目N”这一种写法，避免把正文里的
        714、143 误当成题号。
        """

        crop = frame.crop(
            (
                0,
                max(0, card.header_top - tuning.card_header_pad),
                min(frame.size[0], tuning.card_header_width),
                min(frame.size[1], card.header_top + tuning.card_header_height),
            )
        )
        text = ocr.text(crop, lang=tuning.ocr_lang, config="--psm 7")
        match = re.search(const.CARD_HEADER_NUMBER_PATTERN, text)
        return int(match.group(1)) if match else None

    @staticmethod
    def footer_type(
        frame: Image.Image, card: Card, ocr: OcrClient, tuning: Tuning
    ) -> str | None:
        """
        从页脚那行灰字里读题型：“二、需求与供给 | 单选题 | 易” -> 单选题。

        混合试卷里每类题型的题号都从 1 开始，只能靠题型把两段题号隔开。
        页脚格式是「章节标题 | 题型 | 难度」，优先认第二段。
        """

        if card.footer <= 0:
            return None

        scale = frame.size[0] / tuning.screen_width
        top = max(
            0, int(round((card.footer - tuning.paper_footer_pad) * scale))
        )
        bottom = min(
            frame.size[1],
            int(round((card.footer + tuning.paper_footer_height) * scale)),
        )
        right = min(
            frame.size[0], int(round(tuning.paper_footer_width * scale))
        )

        text = ocr.text(
            frame.crop((0, top, right, bottom)),
            lang=tuning.ocr_lang,
            config=tuning.paper_footer_psm,
        )

        # 先只看“题型”那一段，免得章节名里也带题型关键字
        fields = [re.sub(r"\s+", "", field) for field in text.split("|")]
        for field in (fields[1:2] if len(fields) > 1 else []) + fields:
            for kind in tuning.paper_types:
                if kind in field:
                    return kind
        return None

    @staticmethod
    def crop(frame: Image.Image, card: Card, tuning: Tuning) -> Image.Image:
        """按题卡裁图：左右整幅，上下留白，下沿停在页脚之前。"""

        width, height = frame.size
        scale = width / tuning.screen_width
        top = max(
            0, int(round((card.top - tuning.card_top_margin) * scale))
        )
        bottom = min(
            height, int(round((card.bottom + tuning.card_bottom_margin) * scale))
        )
        if card.footer > 0:
            bottom = min(
                bottom, int(round((card.footer - tuning.card_footer_gap) * scale))
            )
        return frame.crop((0, top, width, max(top + 1, bottom)))

    @staticmethod
    def fingerprint(image: Image.Image, tuning: Tuning) -> np.ndarray:
        """题卡的黑白缩略图（True 表示有字），用于编号读不出时的兜底去重。"""

        gray = np.asarray(
            image.convert("L").resize(tuning.thumb_size), dtype=int
        )
        return gray < tuning.thumb_ink_lum
