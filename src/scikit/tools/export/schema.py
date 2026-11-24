# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 采集导出工具的设置 schema                             #
# ================================================================== #
# 字段分成设备/屏幕/采集/题卡/滑动/整卷/OCR/版面/Word 九组。
# 字段的默认值来自 const.DEFAULT_EXPORT_SETTINGS，校验范围来自
# const.EXPORT_FIELD_LIMITS；这里只描述“字段叫什么、什么类型、什么提示”。

from __future__ import annotations

from scikit import const
from scikit.platform.schema import Field, Group, SettingsSchema

D = const.DEFAULT_EXPORT_SETTINGS


def field(
    key: str,
    label: str,
    type_: str,
    default,
    *,
    hint: str = "",
    pick: str = "dir",
) -> Field:
    """按 const.EXPORT_FIELD_LIMITS 补上 min/max/step/digits/unit。"""

    rule = const.EXPORT_FIELD_LIMITS.get(key)
    kwargs = {"hint": hint, "pick": pick}
    if rule is not None:
        minimum, maximum, step, digits, unit = rule
        kwargs.update(
            min=minimum,
            max=maximum,
            step=step,
            digits=digits,
            unit=unit,
        )
    return Field(key, label, type_, default, **kwargs)


SCHEMA = SettingsSchema(
    version=const.SETTINGS_SCHEMA_VERSION,
    groups=[
        Group(
            "device",
            "export.settings.device",
            [
                field(
                    "device.adbPath",
                    "export.field.adbPath",
                    "path",
                    D["device"]["adbPath"],
                    pick="file",
                    hint="export.hint.adbPath",
                ),
                field(
                    "device.serial",
                    "export.field.serial",
                    "string",
                    D["device"]["serial"],
                ),
                field(
                    "device.connectAddress",
                    "export.field.connectAddress",
                    "string",
                    D["device"]["connectAddress"],
                    hint="export.hint.connectAddress",
                ),
                field(
                    "device.allowMouseFallback",
                    "export.field.allowMouseFallback",
                    "bool",
                    D["device"]["allowMouseFallback"],
                    hint="export.hint.allowMouseFallback",
                ),
                field(
                    "device.windowKeywords",
                    "export.field.windowKeywords",
                    "string",
                    D["device"]["windowKeywords"],
                    hint="export.hint.windowKeywords",
                ),
            ],
        ),
        Group(
            "screen",
            "export.settings.screen",
            [
                field(
                    "screen.width",
                    "export.field.screenWidth",
                    "int",
                    D["screen"]["width"],
                ),
                field(
                    "screen.height",
                    "export.field.screenHeight",
                    "int",
                    D["screen"]["height"],
                ),
            ],
        ),
        Group(
            "capture",
            "export.settings.capture",
            [
                field(
                    "capture.pages",
                    "export.field.pages",
                    "int",
                    D["capture"]["pages"],
                    hint="export.hint.pages",
                ),
                field(
                    "capture.types",
                    "export.field.types",
                    "string",
                    D["capture"]["types"],
                    hint="export.hint.types",
                ),
                field(
                    "capture.paperTypes",
                    "export.field.paperTypes",
                    "string",
                    D["capture"]["paperTypes"],
                    hint="export.hint.paperTypes",
                ),
                field(
                    "capture.warmup",
                    "export.field.warmup",
                    "float",
                    D["capture"]["warmup"],
                ),
            ],
        ),
        Group(
            "card",
            "export.settings.card",
            [
                field("card.safeTop", "export.field.safeTop", "int", D["card"]["safeTop"]),
                field("card.topMargin", "export.field.topMargin", "int", D["card"]["topMargin"]),
                field("card.bottomMargin", "export.field.bottomMargin", "int", D["card"]["bottomMargin"]),
                field("card.footerGap", "export.field.footerGap", "int", D["card"]["footerGap"]),
                field("card.redR", "export.field.redR", "int", D["card"]["redR"]),
                field("card.redG", "export.field.redG", "int", D["card"]["redG"]),
                field("card.redB", "export.field.redB", "int", D["card"]["redB"]),
                field("card.darkLum", "export.field.darkLum", "int", D["card"]["darkLum"]),
                field("card.footerLum", "export.field.footerLum", "int", D["card"]["footerLum"]),
                field("card.footerWidth", "export.field.footerWidth", "int", D["card"]["footerWidth"]),
                field("card.footerMin", "export.field.footerMin", "int", D["card"]["footerMin"]),
                field("card.targetHeaderTop", "export.field.targetHeaderTop", "int", D["card"]["targetHeaderTop"]),
                field("card.sameRatio", "export.field.sameRatio", "float", D["card"]["sameRatio"]),
                field("card.selectionRatio", "export.field.selectionRatio", "float", D["card"]["selectionRatio"]),
                field("card.selectionTapX", "export.field.selectionTapX", "int", D["card"]["selectionTapX"]),
                field("card.selectionTapY", "export.field.selectionTapY", "int", D["card"]["selectionTapY"]),
            ],
        ),
        Group(
            "swipe",
            "export.settings.swipe",
            [
                field("swipe.duration", "export.field.swipeDuration", "int", D["swipe"]["duration"]),
                field("swipe.minDuration", "export.field.swipeMinDuration", "int", D["swipe"]["minDuration"]),
                field("swipe.msPerPixel", "export.field.msPerPixel", "int", D["swipe"]["msPerPixel"]),
                field("swipe.maxRatio", "export.field.maxRatio", "float", D["swipe"]["maxRatio"]),
                field("swipe.startXRatio", "export.field.startXRatio", "float", D["swipe"]["startXRatio"]),
                field("swipe.startYRatio", "export.field.startYRatio", "float", D["swipe"]["startYRatio"]),
                field("swipe.dragDuration", "export.field.dragDuration", "float", D["swipe"]["dragDuration"]),
                field("swipe.holdBeforeRelease", "export.field.holdBeforeRelease", "float", D["swipe"]["holdBeforeRelease"]),
            ],
        ),
        Group(
            "paper",
            "export.settings.paper",
            [
                field("paper.typeCheckEvery", "export.field.typeCheckEvery", "int", D["paper"]["typeCheckEvery"]),
                field("paper.jump", "export.field.paperJump", "int", D["paper"]["jump"]),
                field("paper.recent", "export.field.paperRecent", "int", D["paper"]["recent"]),
                field("paper.footerPsm", "export.field.footerPsm", "string", D["paper"]["footerPsm"]),
                field("paper.footerWidth", "export.field.paperFooterWidth", "int", D["paper"]["footerWidth"]),
                field("paper.footerPad", "export.field.paperFooterPad", "int", D["paper"]["footerPad"]),
                field("paper.footerHeight", "export.field.paperFooterHeight", "int", D["paper"]["footerHeight"]),
            ],
        ),
        Group(
            "ocr",
            "export.settings.ocr",
            [
                field(
                    "ocr.tesseractPath",
                    "export.field.tesseractPath",
                    "path",
                    D["ocr"]["tesseractPath"],
                    pick="file",
                    hint="export.hint.tesseractPath",
                ),
                field("ocr.lang", "export.field.ocrLang", "string", D["ocr"]["lang"]),
                field("ocr.config", "export.field.ocrConfig", "string", D["ocr"]["config"]),
                field("ocr.scale", "export.field.ocrScale", "int", D["ocr"]["scale"]),
                field("ocr.markMath", "export.field.markMath", "bool", D["ocr"]["markMath"]),
                field("ocr.timeout", "export.field.ocrTimeout", "int", D["ocr"]["timeout"]),
            ],
        ),
        Group(
            "shape",
            "export.settings.shape",
            [
                field("shape.darkLum", "export.field.shapeDarkLum", "int", D["shape"]["darkLum"]),
                field("shape.tableHRatio", "export.field.tableHRatio", "float", D["shape"]["tableHRatio"]),
                field("shape.tableHMin", "export.field.tableHMin", "int", D["shape"]["tableHMin"]),
                field("shape.tableVRatio", "export.field.tableVRatio", "float", D["shape"]["tableVRatio"]),
                field("shape.tableVMin", "export.field.tableVMin", "int", D["shape"]["tableVMin"]),
                field("shape.tableHLines", "export.field.tableHLines", "int", D["shape"]["tableHLines"]),
                field("shape.tableVLines", "export.field.tableVLines", "int", D["shape"]["tableVLines"]),
                field("shape.figureSpan", "export.field.figureSpan", "int", D["shape"]["figureSpan"]),
                field("shape.lineGap", "export.field.lineGap", "int", D["shape"]["lineGap"]),
            ],
        ),
        Group(
            "word",
            "export.settings.word",
            [
                field("word.font", "export.field.wordFont", "string", D["word"]["font"]),
                field("word.fontSize", "export.field.wordFontSize", "float", D["word"]["fontSize"]),
                field("word.titleSuffix", "export.field.wordTitleSuffix", "string", D["word"]["titleSuffix"]),
                field("word.questionTitle", "export.field.wordQuestionTitle", "string", D["word"]["questionTitle"]),
            ],
        ),
    ],
)
