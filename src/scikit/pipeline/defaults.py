# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 调参对象 Tuning：把 const 里的算法默认值组装成不可变对象 #
# ================================================================== #
# 所有默认值都在 scikit/const.py 的 DEFAULT_TUNING 里，这里只负责：
#   - 定义字段并引用这些默认值；
#   - 从工具设置（点号路径）生成一次任务使用的 Tuning。
# 这样业务代码不会散落魔法数字，改默认值只需要改 const.py。

from __future__ import annotations

from dataclasses import dataclass, field

from scikit import const
from scikit.platform.schema import get_path

_D = const.DEFAULT_TUNING


def split_list(value: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
    """把逗号/顿号/换行分隔的字符串拆成元组，去空、去重、保持顺序。"""

    if not value or not str(value).strip():
        return fallback
    parts = str(value).replace("，", ",").replace("、", ",").replace("\n", ",")
    result: list[str] = []
    for item in parts.split(","):
        name = item.strip()
        if name and name not in result:
            result.append(name)
    return tuple(result) or fallback


@dataclass(frozen=True)
class Tuning:
    """一次任务使用的全部算法参数（不可变，可安全传进任务线程）。"""

    # ------ 模拟器分辨率 ------ #
    screen_width: int = _D["screen_width"]
    screen_height: int = _D["screen_height"]

    # ------ 题卡构图与识别 ------ #
    card_safe_top: int = _D["card_safe_top"]
    card_top_margin: int = _D["card_top_margin"]
    card_bottom_margin: int = _D["card_bottom_margin"]
    card_footer_gap: int = _D["card_footer_gap"]
    card_red: tuple[int, int, int] = _D["card_red"]
    card_dark_lum: int = _D["card_dark_lum"]
    card_footer_lum: int = _D["card_footer_lum"]
    card_footer_width: int = _D["card_footer_width"]
    card_footer_min: int = _D["card_footer_min"]
    card_header_width: int = _D["card_header_width"]
    card_header_pad: int = _D["card_header_pad"]
    card_header_height: int = _D["card_header_height"]
    target_header_top: int = _D["target_header_top"]
    thumb_width: int = _D["thumb_width"]
    thumb_height: int = _D["thumb_height"]
    thumb_ink_lum: int = _D["thumb_ink_lum"]
    same_ratio: float = _D["same_ratio"]
    selection_ratio: float = _D["selection_ratio"]
    selection_tap: tuple[int, int] = _D["selection_tap"]

    # ------ 滑动 ------ #
    adb_duration: int = _D["adb_duration"]
    adb_min_duration: int = _D["adb_min_duration"]
    adb_ms_per_pixel: int = _D["adb_ms_per_pixel"]
    max_swipe_ratio: float = _D["max_swipe_ratio"]
    start_x_ratio: float = _D["start_x_ratio"]
    start_y_ratio: float = _D["start_y_ratio"]
    drag_duration: float = _D["drag_duration"]
    hold_before_release: float = _D["hold_before_release"]

    # ------ 混合试卷 ------ #
    paper_type_check_every: int = _D["paper_type_check_every"]
    paper_jump: int = _D["paper_jump"]
    paper_recent: int = _D["paper_recent"]
    paper_footer_psm: str = _D["paper_footer_psm"]
    paper_footer_width: int = _D["paper_footer_width"]
    paper_footer_pad: int = _D["paper_footer_pad"]
    paper_footer_height: int = _D["paper_footer_height"]
    paper_types: tuple[str, ...] = _D["paper_types"]

    # ------ OCR ------ #
    ocr_lang: str = _D["ocr_lang"]
    ocr_config: str = _D["ocr_config"]
    ocr_scale: int = _D["ocr_scale"]
    ocr_mark_math: bool = _D["ocr_mark_math"]
    ocr_timeout: int = _D["ocr_timeout"]

    # ------ 版面判断 ------ #
    shape_dark_lum: int = _D["shape_dark_lum"]
    shape_table_h_ratio: float = _D["shape_table_h_ratio"]
    shape_table_h_min: int = _D["shape_table_h_min"]
    shape_table_v_ratio: float = _D["shape_table_v_ratio"]
    shape_table_v_min: int = _D["shape_table_v_min"]
    shape_table_h_lines: int = _D["shape_table_h_lines"]
    shape_table_v_lines: int = _D["shape_table_v_lines"]
    shape_figure_span: int = _D["shape_figure_span"]
    shape_line_gap: int = _D["shape_line_gap"]

    # ------ Word ------ #
    word_font: str = _D["word_font"]
    word_font_size: float = _D["word_font_size"]
    word_title_suffix: str = _D["word_title_suffix"]
    word_question_title: str = _D["word_question_title"]

    # ------ 采集 ------ #
    pages: int = _D["pages"]
    warmup: float = _D["warmup"]
    png_types: tuple[str, ...] = _D["png_types"]

    # ------ 常量派生 ------ #
    ocr_kind_suffix: dict = field(
        default_factory=lambda: dict(const.OCR_KIND_SUFFIX)
    )
    ocr_kind_order: tuple[str, ...] = const.OCR_KIND_ORDER
    kind_labels: dict = field(default_factory=lambda: dict(const.OCR_KIND_LABELS))

    @property
    def thumb_size(self) -> tuple[int, int]:
        """去重指纹的缩略图尺寸。"""

        return (self.thumb_width, self.thumb_height)

    @classmethod
    def from_settings(cls, settings: dict) -> Tuning:
        """
        从工具设置生成 Tuning；缺项一律回落到 const.DEFAULT_TUNING。

        设置里的 key 用点号路径（card.safeTop 等），与 schema.py 一致。
        """

        def num(key: str, default: float) -> float:
            try:
                return float(get_path(settings, key, default))
            except (TypeError, ValueError):
                return default

        def integer(key: str, default: int) -> int:
            return int(round(num(key, default)))

        def boolean(key: str, default: bool) -> bool:
            value = get_path(settings, key, default)
            return bool(value)

        def string(key: str, default: str) -> str:
            value = get_path(settings, key, default)
            return str(value) if value is not None else default

        red = (
            integer("card.redR", _D["card_red"][0]),
            integer("card.redG", _D["card_red"][1]),
            integer("card.redB", _D["card_red"][2]),
        )
        tap_x = integer("card.selectionTapX", _D["selection_tap"][0])
        tap_y = integer("card.selectionTapY", _D["selection_tap"][1])

        return cls(
            screen_width=integer("screen.width", _D["screen_width"]),
            screen_height=integer("screen.height", _D["screen_height"]),
            # ------ 题卡 ------ #
            card_safe_top=integer("card.safeTop", _D["card_safe_top"]),
            card_top_margin=integer("card.topMargin", _D["card_top_margin"]),
            card_bottom_margin=integer(
                "card.bottomMargin", _D["card_bottom_margin"]
            ),
            card_footer_gap=integer("card.footerGap", _D["card_footer_gap"]),
            card_red=red,
            card_dark_lum=integer("card.darkLum", _D["card_dark_lum"]),
            card_footer_lum=integer("card.footerLum", _D["card_footer_lum"]),
            card_footer_width=integer(
                "card.footerWidth", _D["card_footer_width"]
            ),
            card_footer_min=integer("card.footerMin", _D["card_footer_min"]),
            target_header_top=integer(
                "card.targetHeaderTop", _D["target_header_top"]
            ),
            same_ratio=num("card.sameRatio", _D["same_ratio"]),
            selection_ratio=num("card.selectionRatio", _D["selection_ratio"]),
            selection_tap=(tap_x, tap_y),
            # ------ 滑动 ------ #
            adb_duration=integer("swipe.duration", _D["adb_duration"]),
            adb_min_duration=integer(
                "swipe.minDuration", _D["adb_min_duration"]
            ),
            adb_ms_per_pixel=integer(
                "swipe.msPerPixel", _D["adb_ms_per_pixel"]
            ),
            max_swipe_ratio=num("swipe.maxRatio", _D["max_swipe_ratio"]),
            start_x_ratio=num("swipe.startXRatio", _D["start_x_ratio"]),
            start_y_ratio=num("swipe.startYRatio", _D["start_y_ratio"]),
            drag_duration=num("swipe.dragDuration", _D["drag_duration"]),
            hold_before_release=num(
                "swipe.holdBeforeRelease", _D["hold_before_release"]
            ),
            # ------ 混合试卷 ------ #
            paper_type_check_every=integer(
                "paper.typeCheckEvery", _D["paper_type_check_every"]
            ),
            paper_jump=integer("paper.jump", _D["paper_jump"]),
            paper_recent=integer("paper.recent", _D["paper_recent"]),
            paper_footer_psm=string(
                "paper.footerPsm", _D["paper_footer_psm"]
            )
            or _D["paper_footer_psm"],
            paper_footer_width=integer(
                "paper.footerWidth", _D["paper_footer_width"]
            ),
            paper_footer_pad=integer(
                "paper.footerPad", _D["paper_footer_pad"]
            ),
            paper_footer_height=integer(
                "paper.footerHeight", _D["paper_footer_height"]
            ),
            paper_types=split_list(
                string("capture.paperTypes", ""), const.DEFAULT_PAPER_TYPES
            ),
            # ------ OCR ------ #
            ocr_lang=string("ocr.lang", _D["ocr_lang"]) or _D["ocr_lang"],
            ocr_config=string("ocr.config", _D["ocr_config"])
            or _D["ocr_config"],
            ocr_scale=integer("ocr.scale", _D["ocr_scale"]),
            ocr_mark_math=boolean("ocr.markMath", _D["ocr_mark_math"]),
            ocr_timeout=integer("ocr.timeout", _D["ocr_timeout"]),
            # ------ 版面 ------ #
            shape_dark_lum=integer("shape.darkLum", _D["shape_dark_lum"]),
            shape_table_h_ratio=num(
                "shape.tableHRatio", _D["shape_table_h_ratio"]
            ),
            shape_table_h_min=integer(
                "shape.tableHMin", _D["shape_table_h_min"]
            ),
            shape_table_v_ratio=num(
                "shape.tableVRatio", _D["shape_table_v_ratio"]
            ),
            shape_table_v_min=integer(
                "shape.tableVMin", _D["shape_table_v_min"]
            ),
            shape_table_h_lines=integer(
                "shape.tableHLines", _D["shape_table_h_lines"]
            ),
            shape_table_v_lines=integer(
                "shape.tableVLines", _D["shape_table_v_lines"]
            ),
            shape_figure_span=integer(
                "shape.figureSpan", _D["shape_figure_span"]
            ),
            shape_line_gap=integer("shape.lineGap", _D["shape_line_gap"]),
            # ------ Word ------ #
            word_font=string("word.font", _D["word_font"]) or _D["word_font"],
            word_font_size=num("word.fontSize", _D["word_font_size"]),
            word_title_suffix=string(
                "word.titleSuffix", _D["word_title_suffix"]
            )
            or _D["word_title_suffix"],
            word_question_title=string(
                "word.questionTitle", _D["word_question_title"]
            )
            or _D["word_question_title"],
            # ------ 采集 ------ #
            pages=integer("capture.pages", _D["pages"]),
            warmup=num("capture.warmup", _D["warmup"]),
            png_types=split_list(
                string("capture.types", ""), const.DEFAULT_PNG_TYPES
            ),
        )
