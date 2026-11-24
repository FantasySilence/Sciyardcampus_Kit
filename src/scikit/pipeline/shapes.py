# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 判断题卡版面：有没有表格、有没有插图                   #
# ================================================================== #
# 表格：几条贯穿全宽的横线 + 几条贯穿大半高的竖线；
# 图像：连续一大片行都有墨迹（正常文字行之间一定有空行）。
# 阈值按 1600 宽的题卡标定，换分辨率要跟着改 Tuning。

from __future__ import annotations

import numpy as np
from PIL import Image

from scikit.pipeline.defaults import Tuning


class QuestionShape:
    """判断一道题里有没有表格 / 图像，返回特征标签列表。"""

    @staticmethod
    def lum(image: Image.Image) -> np.ndarray:
        """转成亮度数组（0~255）。"""

        return np.asarray(image.convert("RGB")).astype(int).mean(axis=2)

    @staticmethod
    def has_table(image: Image.Image, tuning: Tuning) -> bool:
        """用长横线 + 长竖线判断表格。"""

        dark = QuestionShape.lum(image) < tuning.shape_dark_lum
        height, width = dark.shape

        # 每一行/每一列里最长的连续暗像素长度
        row_runs = QuestionShape.max_runs(dark, axis=1)
        col_runs = QuestionShape.max_runs(dark, axis=0)

        h_count = int(
            (
                row_runs
                >= max(tuning.shape_table_h_min, int(width * tuning.shape_table_h_ratio))
            ).sum()
        )
        v_count = int(
            (
                col_runs
                >= max(tuning.shape_table_v_min, int(height * tuning.shape_table_v_ratio))
            ).sum()
        )
        return (
            h_count >= tuning.shape_table_h_lines
            and v_count >= tuning.shape_table_v_lines
        )

    @staticmethod
    def has_figure(image: Image.Image, tuning: Tuning) -> bool:
        """连续很多行都有墨迹，判为插图。"""

        dark = QuestionShape.lum(image) < tuning.shape_dark_lum
        ink_rows = dark.any(axis=1)
        return QuestionShape.longest_true_run(ink_rows) >= tuning.shape_figure_span

    @staticmethod
    def kinds(image: Image.Image, tuning: Tuning) -> list[str]:
        """返回 ["table"] / ["image"] / 两者 / 空列表。"""

        result: list[str] = []
        if QuestionShape.has_table(image, tuning):
            result.append("table")
        if QuestionShape.has_figure(image, tuning):
            result.append("image")
        return result

    # ------ 内部 ------ #
    @staticmethod
    def max_runs(mask: np.ndarray, axis: int) -> np.ndarray:
        """
        沿指定轴计算每行/每列最长连续 True 的长度（向量化，避免逐像素 Python 循环）。

        做法：先累加前缀和，再把“最近的 0 位置后的累计”减掉，
        差值就是当前位置结尾的连续 True 长度。
        """

        values = mask.astype(np.int32)
        prefix = np.cumsum(values, axis=axis)
        # 0 的位置把累计值“截断”：每行/列保留到当前为止最后一个 0 的累计
        zeros = np.where(values == 0, prefix, 0)
        # 沿轴向前传播最后一个 0 的累计值；没有 0 时保持 0
        reset = np.maximum.accumulate(zeros, axis=axis)
        lengths = prefix - reset
        return lengths.max(axis=axis)

    @staticmethod
    def longest_true_run(values: np.ndarray) -> int:
        """一维布尔数组里最长的连续 True 长度。"""

        best = 0
        current = 0
        for value in values:
            if value:
                current += 1
                if current > best:
                    best = current
            else:
                current = 0
        return best
