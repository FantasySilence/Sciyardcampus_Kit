# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 全项目唯一的常量表：窗口、路径、设备、算法、Word 默认值 #
# ================================================================== #
# 约定：
#   - 所有“可调常量/默认值”只在这里定义，其它模块一律 from scikit import const；
#   - DEFAULT_TUNING 是算法默认值的唯一来源，Tuning 的字段默认值从这里取；
#   - DEFAULT_EXPORT_SETTINGS 是采集导出工具的出厂设置，也在这里组装；
#   - 业务模块里不再出现魔法数字/魔法字符串。

from __future__ import annotations

# ================================================================== #
# @Description: 应用标识与窗口                                        #
# ================================================================== #
APP_VERSION = "0.1.0"
APP_NAME = "Sciyardcampus Kit"
APP_NAME_CN = "数苑校园工具包"
APP_DIR_NAME = "Sciyardcampus_Kit"
SETTINGS_SCHEMA_VERSION = 1

WINDOW_DEFAULT_WIDTH = 1320
WINDOW_DEFAULT_HEIGHT = 860
WINDOW_MIN_WIDTH = 1040
WINDOW_MIN_HEIGHT = 680
WINDOW_BACKGROUND = "#0b0f18"

# ================================================================== #
# @Description: 数据目录布局                                          #
# ================================================================== #
# 数据根 = 源码运行时是仓库根，打包后是 exe 所在目录；
# 产物统一放 <root>/resources，应用私有文件放 <root>/.scikit。
RESOURCES_DIR_NAME = "resources"
SCIKIT_DIR_NAME = ".scikit"

ROW_PNGS_DIR_NAME = "row_pngs"
ROW_TXT_DIR_NAME = "row_txt"
ROW_PAPER_DIR_NAME = "row_paper"
WORD_OUTPUT_DIR_NAME = "word_output"

PAPER_PNGS_SUBDIR = "pngs"
PAPER_TXTS_SUBDIR = "txts"

SETTINGS_SUBDIR = "settings"
BACKUPS_SUBDIR = "backups"
STORE_MAX_BACKUPS = 5
WEBVIEW_CACHE_DIR_NAME = "webview"
SESSIONS_SUBDIR = "sessions"
PROBE_SUBDIR = "probe"
THUMBS_SUBDIR = "thumbs"
TMP_SUBDIR = "tmp"

PROBE_FILENAME = "probe.png"

# 数据目录解析
DATA_ENV_VAR = "SCIYARDKIT_DATA_DIR"
PORTABLE_FILE = "portable.json"
LOCATION_POINTER_FILE = "location.json"
APPDATA_ENV_VAR = "APPDATA"
APPDATA_FALLBACK_DIR_NAME = ".sciyardcampus_kit"
FALLBACK_DATA_DIR_NAME = "data"
WRITE_PROBE_FILE = ".write-test"

# 只读资源与前端目录
RESOURCE_ICON_SUBDIR = "images"
ICON_FILENAME = "app.ico"
VERSION_FILENAME = "version.json"
WEB_DIR_NAME = "web"
WEB_DIST_DIR_NAME = "dist"
WEB_INDEX_FILENAME = "index.html"

# 开发服务器
DEV_URL_ENV_VAR = "SCIYARDKIT_DEV_URL"
DEFAULT_DEV_URL = "http://127.0.0.1:5173"

# 名称清洗
INVALID_CHARS = '<>:"/\\|?*'
RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)
MAX_NAME_LENGTH = 80
MAX_FILENAME_LENGTH = 120

# 后缀
PNG_SUFFIX = ".png"
TXT_SUFFIX = ".txt"
DOCX_SUFFIX = ".docx"
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})

# ================================================================== #
# @Description: 本地 HTTP 与缩略图                                    #
# ================================================================== #
HTTP_HOST = "127.0.0.1"
HTTP_PORT = 0  # 0 = 让系统分配随机端口
MB_ICONERROR = 0x10
CLIPBOARD_CF_UNICODETEXT = 13
CLIPBOARD_GMEM_MOVEABLE = 0x0002
MEDIA_MIN_THUMB = 64
MEDIA_MAX_THUMB = 1600
MEDIA_DEFAULT_THUMB = 320
MEDIA_MAX_SOURCE_HEIGHT = 100000
MEDIA_ROUTE = "/media"

# ================================================================== #
# @Description: 任务系统                                              #
# ================================================================== #
JOB_MAX_LOGS = 5000
JOB_MAX_ARTIFACTS = 24
JOB_MAX_JOBS = 20

# ================================================================== #
# @Description: adb / 鼠标通道                                        #
# ================================================================== #
CREATE_NO_WINDOW = 0x08000000

ADB_CANDIDATES = (
    r"D:\BlueStacks_nxt_cn\MuMuPlayer\nx_device\15.0\shell\adb.exe",
    r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\adb.exe",
)
ADB_DEFAULT_ADDRESS = "127.0.0.1:16384"
ADB_TIMEOUT = 15
ADB_CAPTURE_TIMEOUT = 30
ADB_CONNECT_TIMEOUT = 20
ADB_SWIPE_TIMEOUT = 20
ADB_TAP_TIMEOUT = 15
ADB_SERVER_TIMEOUT = 20
ADB_ERROR_DETAIL_LIMIT = 400
ADB_MIN_CHUNK_PIXELS = 40
ADB_SWIPE_PAUSE = 0.4
ADB_EDGE_MARGIN = 10
ADB_NETWORK_PREFIXES = ("127.0.0.1:", "localhost:")

WINDOW_TITLE_KEYWORDS = (
    "MuMu",
    "Android",
    "Emulator",
    "模拟器",
    "夜神",
    "雷电",
    "BlueStacks",
)
MOUSE_MIN_WINDOW_WIDTH = 200
MOUSE_MIN_WINDOW_HEIGHT = 200
MOUSE_MOVE_PAUSE = 0.05
MOUSE_STEP_PIXELS = 10
MOUSE_MIN_STEPS = 8

# ================================================================== #
# @Description: OCR                                                   #
# ================================================================== #
OCR_VERSION_TIMEOUT = 15
OCR_LANGS_TIMEOUT = 15
OCR_ERROR_DETAIL_LIMIT = 500

# ================================================================== #
# @Description: 算法默认值（DEFAULT_TUNING 是唯一来源）                #
# ================================================================== #
DEFAULT_PNG_TYPES = ("选择题", "分析题", "画图题", "计算题")
DEFAULT_PAPER_TYPES = (
    "单选题",
    "多选题",
    "判断题",
    "填空题",
    "选择题",
    "分析题",
    "计算题",
    "画图题",
    "问答题",
    "简答题",
    "论述题",
    "应用题",
    "证明题",
)

OCR_KIND_SUFFIX = {"formula": "_formula", "table": "_table", "image": "_image"}
OCR_KIND_ORDER = ("formula", "table", "image")
OCR_KIND_LABELS = {"formula": "含公式", "table": "含表格", "image": "含图像"}

# Word 导出模式：auto = 有标签贴图、无标签转文字；text/image = 用户显式指定
EXPORT_MODES = ("auto", "text", "image")
DEFAULT_EXPORT_MODE = "auto"
# 单题文字编辑上限：防止把超大文本塞进会话/Word
MAX_TEXT_EDIT_LENGTH = 200000

# 公式里的排版符号 -> LaTeX
MATH_SYMBOLS = {
    "\u00d7": r"\times ",
    "\u00f7": r"\div ",
    "\u2264": r"\leq ",
    "\u2265": r"\geq ",
    "\u2260": r"\neq ",
    "\u00b7": r"\cdot ",
}

# 文本分段与公式识别的正则（字符串形式，textfmt 里编译）
TEXT_OPTION_PATTERN = r"^[ABCD][\s\u4e00-\u9fff]"
TEXT_SUB_ITEM_PATTERN = r"^[（(]\d+[）)]"
TEXT_MATH_PATTERN = (
    r"(?<![A-Za-z])(?:(?![A-Za-z]{3})"
    r"[A-Za-z0-9()\[\]{}^_.,+\-*/=<>\u00b7\u00d7\u00f7\u2264\u2265\u2260 ]){3,}"
    r"(?![A-Za-z])"
)
TEXT_FORMULA_WORD_PATTERN = r"[A-Za-z]{3,}"
TEXT_FORMULA_DIGIT_LETTER_PATTERN = r"[A-Za-z]\d|\d[A-Za-z]"
TEXT_TRAILING_PUNCT = ",.;:，。；："
TEXT_LINE_ALNUM_MIN = 3
TEXT_LINE_ASCII_RATIO = 0.6
TEXT_FORMULA_MIN_LENGTH = 3
TEXT_FORMULA_OPERATORS = ("=", "^", "_")

# 题卡标题里的“题目N”
CARD_HEADER_NUMBER_PATTERN = r"题\s*目\s*(\d{1,3})"

# 历史/默认标题
DEFAULT_PAPER_TITLE = "未命名试卷"
DEFAULT_TYPE_TITLE = "未命名题型"

# 采集循环
CAPTURE_STILL_LIMIT = 3
CAPTURE_TALL_RATIO = 0.75
CAPTURE_SELECTION_WAIT = 0.8
CAPTURE_FRAME_WAIT = 1.0
CAPTURE_STILL_RETRY_RATIO = 0.6
CAPTURE_STILL_RETRY_FACTOR = 1.2
CAPTURE_STILL_RETRY_MIN_SCROLL = 60
CAPTURE_PAGES_MIN = 1
CAPTURE_PAGES_MAX = 5000
CAPTURE_DEFAULT_SCROLL_RATIO = 0.5
CAPTURE_TARGET_SCROLL_MIN_RATIO = 0.5
CAPTURE_TARGET_SCROLL_MAX_RATIO = 0.8
CAPTURE_TALL_SKIP_SCROLL = 20
SELECTION_BLUE_MIN = 180
SELECTION_BLUE_RED_DIFF = 40

# 致命 OCR 错误码：整批停止，让用户先修环境
FATAL_OCR_CODES = frozenset(
    {
        "TESSERACT_MISSING",
        "TESSERACT_FAILED",
        "TESSERACT_TIMEOUT",
        "TESSERACT_LANG_MISSING",
    }
)

# Word 页面（A4 + 2.54cm 页边距）
WORD_PAGE_WIDTH_CM = 21
WORD_PAGE_HEIGHT_CM = 29.7
WORD_PAGE_MARGIN_CM = 2.54
WORD_DEFAULT_PAPER_NAME = "试卷"
WORD_DEFAULT_TYPE_NAME = "题目"
TXT_PARAGRAPH_SEPARATOR = "\n\n"

DEFAULT_TUNING = {
    # 模拟器分辨率
    "screen_width": 1600,
    "screen_height": 900,
    # 题卡构图与识别
    "card_safe_top": 130,
    "card_top_margin": 30,
    "card_bottom_margin": 52,
    "card_footer_gap": 10,
    "card_red": (200, 80, 80),
    "card_dark_lum": 140,
    "card_footer_lum": 165,
    "card_footer_width": 500,
    "card_footer_min": 6,
    "card_header_width": 430,
    "card_header_pad": 4,
    "card_header_height": 34,
    "target_header_top": 220,
    "thumb_width": 200,
    "thumb_height": 60,
    "thumb_ink_lum": 170,
    "same_ratio": 0.008,
    "selection_ratio": 0.003,
    "selection_tap": (1550, 450),
    # 滑动
    "adb_duration": 1500,
    "adb_min_duration": 300,
    "adb_ms_per_pixel": 3,
    "max_swipe_ratio": 0.6,
    "start_x_ratio": 0.5,
    "start_y_ratio": 0.8,
    "drag_duration": 0.45,
    "hold_before_release": 0.2,
    # 混合试卷
    "paper_type_check_every": 5,
    "paper_jump": 4,
    "paper_recent": 5,
    "paper_footer_psm": "--psm 7",
    "paper_footer_width": 620,
    "paper_footer_pad": 6,
    "paper_footer_height": 26,
    "paper_types": DEFAULT_PAPER_TYPES,
    # OCR
    "ocr_lang": "chi_sim+eng",
    "ocr_config": "--psm 6",
    "ocr_scale": 1,
    "ocr_mark_math": True,
    "ocr_timeout": 60,
    # 版面判断
    "shape_dark_lum": 160,
    "shape_table_h_ratio": 0.18,
    "shape_table_h_min": 120,
    "shape_table_v_ratio": 0.12,
    "shape_table_v_min": 60,
    "shape_table_h_lines": 3,
    "shape_table_v_lines": 3,
    "shape_figure_span": 100,
    "shape_line_gap": 3,
    # Word
    "word_font": "宋体",
    "word_font_size": 10.5,
    "word_title_suffix": "题库",
    "word_question_title": "第%d题",
    # 采集
    "pages": 200,
    "warmup": 2.0,
    "png_types": DEFAULT_PNG_TYPES,
}

# ================================================================== #
# @Description: 工具出厂设置                                          #
# ================================================================== #
# 设置字段的校验范围：(min, max, step, digits, unit)
EXPORT_FIELD_LIMITS = {
    "screen.width": (800, 3840, 10, 4, ""),
    "screen.height": (600, 2160, 10, 4, ""),
    "capture.pages": (1, 5000, 1, 4, ""),
    "capture.warmup": (0, 30, 0.5, 1, "秒"),
    "card.safeTop": (0, 600, 5, 4, ""),
    "card.topMargin": (0, 200, 1, 4, ""),
    "card.bottomMargin": (0, 200, 1, 4, ""),
    "card.footerGap": (0, 100, 1, 4, ""),
    "card.redR": (0, 255, 1, 4, ""),
    "card.redG": (0, 255, 1, 4, ""),
    "card.redB": (0, 255, 1, 4, ""),
    "card.darkLum": (0, 255, 1, 4, ""),
    "card.footerLum": (0, 255, 1, 4, ""),
    "card.footerWidth": (100, 1600, 10, 4, ""),
    "card.footerMin": (0, 100, 1, 4, ""),
    "card.targetHeaderTop": (0, 900, 10, 4, ""),
    "card.sameRatio": (0, 0.1, 0.001, 3, ""),
    "card.selectionRatio": (0, 0.1, 0.001, 3, ""),
    "card.selectionTapX": (0, 1920, 10, 4, ""),
    "card.selectionTapY": (0, 1080, 10, 4, ""),
    "swipe.duration": (100, 5000, 50, 0, "毫秒"),
    "swipe.minDuration": (100, 2000, 50, 0, "毫秒"),
    "swipe.msPerPixel": (1, 20, 1, 4, ""),
    "swipe.maxRatio": (0.1, 1, 0.05, 2, ""),
    "swipe.startXRatio": (0, 1, 0.05, 2, ""),
    "swipe.startYRatio": (0, 1, 0.05, 2, ""),
    "swipe.dragDuration": (0.1, 3, 0.05, 2, "秒"),
    "swipe.holdBeforeRelease": (0, 2, 0.05, 2, "秒"),
    "paper.typeCheckEvery": (1, 50, 1, 4, ""),
    "paper.jump": (1, 50, 1, 4, ""),
    "paper.recent": (1, 20, 1, 4, ""),
    "paper.footerWidth": (100, 1600, 10, 4, ""),
    "paper.footerPad": (0, 50, 1, 4, ""),
    "paper.footerHeight": (5, 100, 1, 4, ""),
    "ocr.scale": (1, 3, 1, 4, ""),
    "ocr.timeout": (10, 300, 5, 0, "秒"),
    "shape.darkLum": (0, 255, 1, 4, ""),
    "shape.tableHRatio": (0, 1, 0.01, 2, ""),
    "shape.tableHMin": (10, 1600, 10, 4, ""),
    "shape.tableVRatio": (0, 1, 0.01, 2, ""),
    "shape.tableVMin": (10, 900, 10, 4, ""),
    "shape.tableHLines": (1, 20, 1, 4, ""),
    "shape.tableVLines": (1, 20, 1, 4, ""),
    "shape.figureSpan": (10, 900, 10, 4, ""),
    "shape.lineGap": (0, 20, 1, 4, ""),
    "word.fontSize": (5, 30, 0.5, 1, "磅"),
}

APP_PREFS_DEFAULT = {
    "language": "zh_CN",
    "theme": "dark",
    "lastTool": "export",
    "window": {},
}

DEFAULT_EXPORT_SETTINGS = {
    "device": {
        "adbPath": "",
        "serial": "",
        "connectAddress": ADB_DEFAULT_ADDRESS,
        "allowMouseFallback": False,
        "windowKeywords": ",".join(WINDOW_TITLE_KEYWORDS),
    },
    "screen": {
        "width": DEFAULT_TUNING["screen_width"],
        "height": DEFAULT_TUNING["screen_height"],
    },
    "capture": {
        "pages": DEFAULT_TUNING["pages"],
        "types": ",".join(DEFAULT_PNG_TYPES),
        "paperTypes": ",".join(DEFAULT_PAPER_TYPES),
        "warmup": DEFAULT_TUNING["warmup"],
    },
    "card": {
        "safeTop": DEFAULT_TUNING["card_safe_top"],
        "topMargin": DEFAULT_TUNING["card_top_margin"],
        "bottomMargin": DEFAULT_TUNING["card_bottom_margin"],
        "footerGap": DEFAULT_TUNING["card_footer_gap"],
        "redR": DEFAULT_TUNING["card_red"][0],
        "redG": DEFAULT_TUNING["card_red"][1],
        "redB": DEFAULT_TUNING["card_red"][2],
        "darkLum": DEFAULT_TUNING["card_dark_lum"],
        "footerLum": DEFAULT_TUNING["card_footer_lum"],
        "footerWidth": DEFAULT_TUNING["card_footer_width"],
        "footerMin": DEFAULT_TUNING["card_footer_min"],
        "targetHeaderTop": DEFAULT_TUNING["target_header_top"],
        "sameRatio": DEFAULT_TUNING["same_ratio"],
        "selectionRatio": DEFAULT_TUNING["selection_ratio"],
        "selectionTapX": DEFAULT_TUNING["selection_tap"][0],
        "selectionTapY": DEFAULT_TUNING["selection_tap"][1],
    },
    "swipe": {
        "duration": DEFAULT_TUNING["adb_duration"],
        "minDuration": DEFAULT_TUNING["adb_min_duration"],
        "msPerPixel": DEFAULT_TUNING["adb_ms_per_pixel"],
        "maxRatio": DEFAULT_TUNING["max_swipe_ratio"],
        "startXRatio": DEFAULT_TUNING["start_x_ratio"],
        "startYRatio": DEFAULT_TUNING["start_y_ratio"],
        "dragDuration": DEFAULT_TUNING["drag_duration"],
        "holdBeforeRelease": DEFAULT_TUNING["hold_before_release"],
    },
    "paper": {
        "typeCheckEvery": DEFAULT_TUNING["paper_type_check_every"],
        "jump": DEFAULT_TUNING["paper_jump"],
        "recent": DEFAULT_TUNING["paper_recent"],
        "footerPsm": DEFAULT_TUNING["paper_footer_psm"],
        "footerWidth": DEFAULT_TUNING["paper_footer_width"],
        "footerPad": DEFAULT_TUNING["paper_footer_pad"],
        "footerHeight": DEFAULT_TUNING["paper_footer_height"],
    },
    "ocr": {
        "tesseractPath": "",
        "lang": DEFAULT_TUNING["ocr_lang"],
        "config": DEFAULT_TUNING["ocr_config"],
        "scale": DEFAULT_TUNING["ocr_scale"],
        "markMath": DEFAULT_TUNING["ocr_mark_math"],
        "timeout": DEFAULT_TUNING["ocr_timeout"],
    },
    "shape": {
        "darkLum": DEFAULT_TUNING["shape_dark_lum"],
        "tableHRatio": DEFAULT_TUNING["shape_table_h_ratio"],
        "tableHMin": DEFAULT_TUNING["shape_table_h_min"],
        "tableVRatio": DEFAULT_TUNING["shape_table_v_ratio"],
        "tableVMin": DEFAULT_TUNING["shape_table_v_min"],
        "tableHLines": DEFAULT_TUNING["shape_table_h_lines"],
        "tableVLines": DEFAULT_TUNING["shape_table_v_lines"],
        "figureSpan": DEFAULT_TUNING["shape_figure_span"],
        "lineGap": DEFAULT_TUNING["shape_line_gap"],
    },
    "word": {
        "font": DEFAULT_TUNING["word_font"],
        "fontSize": DEFAULT_TUNING["word_font_size"],
        "titleSuffix": DEFAULT_TUNING["word_title_suffix"],
        "questionTitle": DEFAULT_TUNING["word_question_title"],
    },
}
