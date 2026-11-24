# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 切题算法测试（使用上游留下的 1600x900 整屏）           #
# ================================================================== #

from __future__ import annotations

import pytest
from PIL import Image

from scikit.pipeline.cards import QuestionCard
from scikit.pipeline.defaults import Tuning


def test_split_finds_two_complete_cards(probe_frame: Image.Image, tuning: Tuning) -> None:
    cards = QuestionCard.split(probe_frame, tuning)
    assert len(cards) == 2
    for card in cards:
        assert card.complete(tuning) is True
        assert card.header_top < card.top < card.bottom
        assert card.footer > card.bottom


def test_crop_keeps_full_width(probe_frame: Image.Image, tuning: Tuning) -> None:
    card = QuestionCard.split(probe_frame, tuning)[0]
    cropped = QuestionCard.crop(probe_frame, card, tuning)
    assert cropped.width == probe_frame.width
    assert 0 < cropped.height < probe_frame.height


def test_fingerprint_uses_configured_thumb_size(
    probe_frame: Image.Image, tuning: Tuning
) -> None:
    card = QuestionCard.split(probe_frame, tuning)[0]
    image = QuestionCard.crop(probe_frame, card, tuning)
    fingerprint = QuestionCard.fingerprint(image, tuning)
    assert fingerprint.shape == (tuning.thumb_height, tuning.thumb_width)


@pytest.mark.ocr
def test_header_numbers_are_read_from_title(
    probe_frame: Image.Image, tuning: Tuning, tesseract
) -> None:
    numbers = [
        QuestionCard.header_number(probe_frame, card, tesseract, tuning)
        for card in QuestionCard.split(probe_frame, tuning)
    ]
    assert numbers == [21, 22]
