# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 表格 / 插图版面判断测试                                #
# ================================================================== #

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from scikit.pipeline.defaults import Tuning
from scikit.pipeline.shapes import QuestionShape

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_synthetic_grid_is_table(tuning: Tuning) -> None:
    image = Image.new("RGB", (800, 600), "white")
    draw = ImageDraw.Draw(image)
    for y in range(60, 560, 100):
        draw.line((40, y, 760, y), fill="black", width=4)
    for x in range(40, 800, 120):
        draw.line((x, 60, x, 540), fill="black", width=4)

    assert QuestionShape.has_table(image, tuning) is True


def test_question_card_is_not_table(tuning: Tuning) -> None:
    image = Image.open(FIXTURES / "card-273.png").convert("RGB")
    assert QuestionShape.has_table(image, tuning) is False


def test_solid_band_is_figure(tuning: Tuning) -> None:
    image = Image.new("RGB", (800, 600), "white")
    draw = ImageDraw.Draw(image)
    # 连续 150 行都有墨迹，超过默认 figureSpan=100
    draw.rectangle((100, 200, 700, 350), fill="black")
    assert QuestionShape.has_figure(image, tuning) is True
