# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 采集流水线：整卷 / 单题型，复用上游切题与滚动对齐算法   #
# ================================================================== #
# 与上游 GetScreenshot / GetPaperScreenshot 的差异只在“外壳”：
#   - 用 Reporter 汇报日志/进度，用 reporter.sleep 代替 time.sleep；
#   - 每个循环迭代都有取消检查点；
#   - 返回结构化的 items，供会话、预览、导出使用；
#   - 不再 print，也不再固定等待 5 秒（warmup 可配置）。

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence

import numpy as np
from PIL import Image

from scikit import const
from scikit.device.base import Device
from scikit.errors import AppError
from scikit.jobs import Reporter
from scikit.pipeline.artifact_paths import ArtifactPaths
from scikit.pipeline.cards import Card, QuestionCard
from scikit.pipeline.defaults import Tuning, split_list
from scikit.pipeline.ocr import OcrClient


def selection_ratio(frame: Image.Image) -> float:
    """画面里“文本被选中”的蓝色高亮占比。"""

    array = np.asarray(frame.convert("RGB")).astype(int)
    red, blue = array[:, :, 0], array[:, :, 2]
    return float(
        (
            (blue > const.SELECTION_BLUE_MIN)
            & (blue - red > const.SELECTION_BLUE_RED_DIFF)
        ).mean()
    )


def capture_clean(
    device: Device, reporter: Reporter, tuning: Tuning, max_retry: int = 2
) -> Image.Image:
    """
    截一张图；如果发现题干被选中（长按的后遗症），点一下空白处取消再重截。
    """

    frame = device.capture()
    for _ in range(max_retry):
        if selection_ratio(frame) <= tuning.selection_ratio:
            return frame
        reporter.log("检测到文本被选中，点一下空白处取消", "warn")
        device.tap(*tuning.selection_tap)
        reporter.sleep(const.CAPTURE_SELECTION_WAIT)
        frame = device.capture()

    if selection_ratio(frame) > tuning.selection_ratio:
        reporter.log("文本仍处于选中状态，请手动点一下模拟器画面再继续", "error")
    return frame


def probe(
    device: Device,
    ocr: OcrClient,
    paths: ArtifactPaths,
    tuning: Tuning,
    reporter: Reporter,
) -> dict:
    """
    预检：截一屏，保存原图，返回每张题卡的坐标/题号/题型/完整性。

    前端在原图上叠加识别框；不改动任何采集数据。
    """

    reporter.progress(0, 1, "截取当前画面", "probe")
    frame = capture_clean(device, reporter, tuning)
    paths.probe_dir.mkdir(parents=True, exist_ok=True)
    target = paths.probe_dir / const.PROBE_FILENAME
    frame.save(target)
    reporter.log(f"整屏 {frame.size[0]}x{frame.size[1]}，已保存预检图", "info")

    cards = QuestionCard.split(frame, tuning)
    if not cards:
        raise AppError(
            "NO_CARDS",
            "没有识别到题目",
            "请确认模拟器停在试卷预览页，且标题行有红色“（x分）”",
        )

    result: list[dict] = []
    for index, card in enumerate(cards, start=1):
        number = QuestionCard.header_number(frame, card, ocr, tuning)
        kind = QuestionCard.footer_type(frame, card, ocr, tuning)
        data = card.to_dict(number=number, kind=kind)
        data["complete"] = card.complete(tuning)
        data["index"] = index
        result.append(data)
        reporter.log(
            f"第{index}张题卡：第{number if number is not None else '?'}题，"
            f"{kind or '未知题型'}，{'完整' if data['complete'] else '被边缘切掉'}",
            "info",
        )

    reporter.progress(1, 1, "预检完成", "probe")
    return {
        "frame": paths.rel(target),
        "width": frame.size[0],
        "height": frame.size[1],
        "cards": result,
        "channel": device.channel,
    }


def capture_type(
    device: Device,
    paths: ArtifactPaths,
    png_type: str,
    pages: int,
    ocr: OcrClient,
    reporter: Reporter,
    tuning: Tuning,
    *,
    clear_old: bool = False,
) -> list[dict]:
    """
    按题型采集：从当前画面往下截，文件名直接用题目编号。

    png_type: 题型，同时作为子目录名
    pages: 最多截多少道题
    clear_old: 开始前是否清空该题型的旧图
    """

    folder = paths.type_dir(png_type)
    olds = [name for name in os.listdir(folder) if name.endswith(".png")]
    if olds and clear_old:
        for name in olds:
            try:
                os.remove(folder / name)
            except OSError:
                pass
        reporter.log(f"已清空 {png_type} 下 {len(olds)} 张旧图", "warn")
    elif olds:
        reporter.log(f"{png_type} 下已有 {len(olds)} 张旧图，同名的会被覆盖", "warn")

    reporter.progress(0, pages, f"采集 {png_type}", "capture")
    if tuning.warmup > 0:
        reporter.log(f"等待 {tuning.warmup:g} 秒，请把模拟器画面切到前台", "info")
        reporter.sleep(tuning.warmup)

    saved_numbers: list[int] = []
    saved_images: list[np.ndarray] = []
    skipped: list[int] = []
    items: list[dict] = []
    last_frame = None
    still = 0

    for _ in range(pages * 6 + 10):
        reporter.check()
        frame = capture_clean(device, reporter, tuning)
        height = frame.size[1]
        cards = QuestionCard.split(frame, tuning)
        if not cards:
            raise AppError(
                "NO_CARDS",
                "没有识别到题目",
                "请确认模拟器停在试卷页面（标题行要有红色“（x分）”）",
            )

        numbers = [
            QuestionCard.header_number(frame, card, ocr, tuning) for card in cards
        ]

        # 把这一屏里完整露出来的新题都存下来
        for card, number in zip(cards, numbers, strict=False):
            reporter.check()
            if not card.complete(tuning):
                continue
            if number is not None and number in saved_numbers:
                continue

            # 题号只认“上一题+1 ~ 上一题+4”，离谱的一律按没读出来处理
            expected = saved_numbers[-1] + 1 if saved_numbers else None
            if (
                number is not None
                and expected is not None
                and not (expected <= number <= expected + 4)
            ):
                reporter.log(
                    f"读到编号 {number}，和预期的 {expected} 对不上，按未读出处理",
                    "warn",
                )
                number = None

            image = QuestionCard.crop(frame, card, tuning)
            signature = QuestionCard.fingerprint(image, tuning)
            if already_saved(number, signature, saved_numbers, saved_images, tuning):
                continue

            if number is None:
                index = expected if expected is not None else 1
                reporter.log(f"有一题没读出编号，暂存为 {index}.png", "warn")
            else:
                index = number
                if expected is not None and index != expected:
                    reporter.log(
                        f"编号从 {expected} 直接跳到 {index}，中间可能有题没截到",
                        "warn",
                    )

            saved_numbers.append(index)
            saved_images.append(signature)

            png_path = paths.png_path(png_type, index)
            image.save(png_path)
            relative = paths.rel(png_path)
            item = make_item(
                index=index,
                number=index,
                kind=png_type,
                png=relative,
                tags=[],
                extra={"width": image.size[0], "height": image.size[1]},
            )
            items.append(item)
            reporter.artifact(
                relative,
                {"index": index, "number": index, "kind": png_type},
            )
            reporter.log(
                f"已保存 {png_type}/{index}.png（{image.size[0]}x{image.size[1]}）",
                "success",
            )
            reporter.progress(len(items), pages, f"已保存 {len(items)} 题", "capture")

            if len(saved_numbers) >= pages:
                reporter.log(f"已达到 pages={pages}，停止", "warn")
                summary(reporter, items, skipped)
                return items

        # 下一道还没存的题就是目标，按它决定滑多少
        target, target_number = first_unsaved_type(
            frame,
            cards,
            numbers,
            saved_numbers,
            saved_images,
            skipped,
            ocr,
            tuning,
        )
        if target is None:
            scroll = int(height * const.CAPTURE_DEFAULT_SCROLL_RATIO)
        else:
            scroll = target_scroll(target, height, tuning)
            if (
                abs(scroll) <= const.CAPTURE_TALL_SKIP_SCROLL
                and not target.complete(tuning)
            ):
                if target_number is not None and target_number not in skipped:
                    skipped.append(target_number)
                    reporter.log(
                        f"第{target_number}题一屏放不下，已跳过（可手动补截）", "warn"
                    )
                scroll = int(height * const.CAPTURE_TALL_RATIO)

        # 画面没变：先加大距离重试，连续几帧不动才认为到底
        digest = hashlib.md5(frame.tobytes()).hexdigest()
        if digest == last_frame:
            still += 1
            if still >= const.CAPTURE_STILL_LIMIT:
                reporter.log(f"连续 {still} 帧画面没有变化，判定已经到底", "warn")
                break
            reporter.log("画面没有变化，加大距离重试", "warn")
            device.swipe(
                int(height * const.CAPTURE_STILL_RETRY_RATIO)
                if abs(scroll) < const.CAPTURE_STILL_RETRY_MIN_SCROLL
                else int(scroll * const.CAPTURE_STILL_RETRY_FACTOR)
            )
            reporter.sleep(const.CAPTURE_FRAME_WAIT)
            continue

        still = 0
        last_frame = digest
        device.swipe(scroll)
        reporter.sleep(const.CAPTURE_FRAME_WAIT)

    summary(reporter, items, skipped)
    return items


def capture_paper(
    device: Device,
    paths: ArtifactPaths,
    paper: str,
    pages: int,
    ocr: OcrClient,
    reporter: Reporter,
    tuning: Tuning,
) -> list[dict]:
    """
    整卷采集：整卷一次滚到底，按顺序号存图。

    整卷里每类题型的题号都从 1 开始，所以“身份”是 (分区, 题号)，
    分区靠页脚题型确认；文件名用顺序号，避免重名。
    """

    folder = paths.paper_png_dir(paper)
    olds = [name for name in os.listdir(folder) if name.endswith(".png")]
    if olds:
        reporter.log(f"{paper}\\pngs 下已有 {len(olds)} 张旧图，同名的会被覆盖", "warn")

    reporter.progress(0, pages, f"采集 {paper}", "capture")
    if tuning.warmup > 0:
        reporter.log(f"等待 {tuning.warmup:g} 秒，请把试卷滑到最上面", "info")
        reporter.sleep(tuning.warmup)

    seq = 0
    section = 1
    current_type: str | None = None
    last_number: int | None = None
    saved_keys: set[tuple[int, int | None]] = set()
    skipped_keys: set[tuple[int, int | None]] = set()
    recent: list[np.ndarray] = []
    counts: dict[str, int] = {}
    skipped: list[str] = []
    boundaries: list[tuple[int | None, int | None]] = []
    items: list[dict] = []
    last_frame = None
    still = 0

    for _ in range(pages * 6 + 10):
        reporter.check()
        frame = capture_clean(device, reporter, tuning)
        height = frame.size[1]
        cards = QuestionCard.split(frame, tuning)
        if not cards:
            raise AppError(
                "NO_CARDS",
                "没有识别到题目",
                "请确认模拟器停在试卷页面（标题行要有红色“（x分）”）",
            )

        numbers = [
            QuestionCard.header_number(frame, card, ocr, tuning) for card in cards
        ]

        for card, number in zip(cards, numbers, strict=False):
            reporter.check()
            if not card.complete(tuning):
                continue

            # 题号往回走：多半是换题型了，读页脚确认
            if number is not None and last_number is not None and number < last_number:
                kind = QuestionCard.footer_type(frame, card, ocr, tuning)
                pair = (last_number, number)
                if kind is not None and kind == current_type:
                    reporter.log(
                        f"读到编号 {number}，和上一题的 {last_number} 对不上，按未读出处理",
                        "warn",
                    )
                    number = None
                elif pair not in boundaries:
                    boundaries.append(pair)
                    section += 1
                    last_number = None
                    if kind is not None:
                        reporter.log(
                            f"题型切换：{current_type} -> {kind}（下一张存为 {seq + 1}.png）",
                            "info",
                        )
                        current_type = kind
                    else:
                        reporter.log(
                            f"编号从 {pair[0]} 回到 {pair[1]}，当作新的一段（页脚题型没读出来）",
                            "warn",
                        )

            # 题号往前跳太远：当识别错误
            elif (
                number is not None
                and last_number is not None
                and number > last_number + tuning.paper_jump
            ):
                reporter.log(
                    f"读到编号 {number}，和上一题的 {last_number} 差太远，按未读出处理",
                    "warn",
                )
                number = None

            if number is not None and (section, number) in saved_keys:
                continue

            image = QuestionCard.crop(frame, card, tuning)
            signature = QuestionCard.fingerprint(image, tuning)

            if number is None and repeated(signature, recent, tuning):
                continue

            seq += 1
            if number is not None:
                saved_keys.add((section, number))
                last_number = number
            if current_type is None:
                current_type = QuestionCard.footer_type(frame, card, ocr, tuning)

            recent.append(signature)
            if len(recent) > tuning.paper_recent:
                recent.pop(0)

            png_path = paths.paper_png_path(paper, seq)
            image.save(png_path)
            relative = paths.rel(png_path)
            item = make_item(
                index=seq,
                number=number,
                kind=current_type or "未知",
                png=relative,
                tags=[],
                extra={"width": image.size[0], "height": image.size[1]},
            )
            items.append(item)
            reporter.artifact(
                relative,
                {"index": seq, "number": number, "kind": current_type or "未知"},
            )
            reporter.log(
                f"已保存 {paper}/{seq}.png（{current_type or '未知'}，"
                f"题目{number if number is not None else '?'}）",
                "success",
            )
            reporter.progress(seq, pages, f"已保存 {seq} 题", "capture")

            label = current_type or "未知"
            counts[label] = counts.get(label, 0) + 1

            # 整卷题号如果连续（不重置），靠这里换题型标签
            if seq % tuning.paper_type_check_every == 0:
                kind = QuestionCard.footer_type(frame, card, ocr, tuning)
                if kind is not None and kind != current_type:
                    reporter.log(f"题型切换：{current_type} -> {kind}", "info")
                    current_type = kind

            if seq >= pages:
                reporter.log(f"已达到 pages={pages}，停止", "warn")
                summary_paper(reporter, seq, counts, skipped)
                return items

        target, target_number = first_unsaved_paper(
            cards,
            numbers,
            section,
            last_number,
            saved_keys,
            skipped_keys,
            tuning,
        )
        if target is None:
            scroll = int(height * const.CAPTURE_DEFAULT_SCROLL_RATIO)
        else:
            scroll = target_scroll(target, height, tuning)
            if abs(scroll) <= const.CAPTURE_TALL_SKIP_SCROLL:
                key = (section, target_number)
                if key not in skipped_keys:
                    skipped_keys.add(key)
                    label = str(target_number) if target_number is not None else "未知"
                    skipped.append(label)
                    reporter.log(
                        f"编号 {label} 这题一屏放不下，已跳过（可手动补截）", "warn"
                    )
                scroll = int(height * const.CAPTURE_TALL_RATIO)

        digest = hashlib.md5(frame.tobytes()).hexdigest()
        if digest == last_frame:
            still += 1
            if still >= const.CAPTURE_STILL_LIMIT:
                reporter.log(f"连续 {still} 帧画面没有变化，判定已经到底", "warn")
                break
            reporter.log("画面没有变化，加大距离重试", "warn")
            device.swipe(
                int(height * const.CAPTURE_STILL_RETRY_RATIO)
                if abs(scroll) < const.CAPTURE_STILL_RETRY_MIN_SCROLL
                else int(scroll * const.CAPTURE_STILL_RETRY_FACTOR)
            )
            reporter.sleep(const.CAPTURE_FRAME_WAIT)
            continue

        still = 0
        last_frame = digest
        device.swipe(scroll)
        reporter.sleep(const.CAPTURE_FRAME_WAIT)

    summary_paper(reporter, seq, counts, skipped)
    return items


# ================================================================== #
# @Description: 采集内部工具函数                                       #
# ================================================================== #
def make_item(
    index: int,
    number: int | None,
    kind: str,
    png: str,
    tags: Sequence[str],
    extra: dict | None = None,
) -> dict:
    """构造会话里的一个题目条目。"""

    item = {
        "index": int(index),
        "number": number,
        "kind": kind,
        "png": png,
        "txt": "",
        "tags": list(tags),
        "included": True,
        "exportMode": const.DEFAULT_EXPORT_MODE,
        "ocrError": "",
    }
    if extra:
        item.update(extra)
    return item


def already_saved(
    number: int | None,
    signature: np.ndarray,
    saved_numbers: Sequence[int],
    saved_images: Sequence[np.ndarray],
    tuning: Tuning,
) -> bool:
    """这道题是不是已经存过了：编号可靠时看编号，否则退回指纹比较。"""

    if number is not None:
        return number in saved_numbers
    for saved in saved_images:
        if saved.shape != signature.shape:
            continue
        if float(np.logical_xor(saved, signature).mean()) < tuning.same_ratio:
            return True
    return False


def repeated(signature: np.ndarray, recent: Sequence[np.ndarray], tuning: Tuning) -> bool:
    """和最近保存的几张比指纹，防止同一题跨帧存两遍。"""

    for saved in recent:
        if saved.shape != signature.shape:
            continue
        if float(np.logical_xor(saved, signature).mean()) < tuning.same_ratio:
            return True
    return False


def target_scroll(card: Card, height: int, tuning: Tuning) -> int:
    """把这道题的标题行顶到目标位置要滑多少；负数表示往回滑。"""

    scroll = card.header_top - tuning.target_header_top
    return max(
        -int(height * const.CAPTURE_TARGET_SCROLL_MIN_RATIO),
        min(scroll, int(height * const.CAPTURE_TARGET_SCROLL_MAX_RATIO)),
    )


def first_unsaved_type(
    frame: Image.Image,
    cards: Sequence[Card],
    numbers: Sequence[int | None],
    saved_numbers: Sequence[int],
    saved_images: Sequence[np.ndarray],
    skipped: Sequence[int],
    ocr: OcrClient,
    tuning: Tuning,
) -> tuple[Card | None, int | None]:
    """单题型：画面里第一道还没存下来的不完整题。"""

    for card, number in zip(cards, numbers, strict=False):
        if card.complete(tuning):
            continue
        if number is not None:
            if number in saved_numbers or number in skipped:
                continue
            return card, number
        if card.header_top <= tuning.card_safe_top:
            continue
        signature = QuestionCard.fingerprint(
            QuestionCard.crop(frame, card, tuning), tuning
        )
        if already_saved(None, signature, saved_numbers, saved_images, tuning):
            continue
        return card, number
    return None, None


def first_unsaved_paper(
    cards: Sequence[Card],
    numbers: Sequence[int | None],
    section: int,
    last_number: int | None,
    saved_keys: set[tuple[int, int | None]],
    skipped_keys: set[tuple[int, int | None]],
    tuning: Tuning,
) -> tuple[Card | None, int | None]:
    """
    整卷：画面里第一道“被下边缘切掉、还没存过”的题。

    被顶部标题栏压住的卡不算目标：往下滚它自然就完整了，
    拿它当目标会算出几像素的滑动，那种滑动在 Android 眼里就是长按。
    """

    for card, number in zip(cards, numbers, strict=False):
        if card.complete(tuning):
            continue
        if card.header_top <= tuning.card_safe_top:
            continue
        if number is not None:
            key = (section, number)
            if key in skipped_keys:
                continue
            if key in saved_keys and number > (last_number or 0):
                continue
        return card, number
    return None, None


def summary(reporter: Reporter, items: Sequence[dict], skipped: Sequence[int]) -> None:
    """单题型采集结束汇报。"""

    reporter.log(f"本次共保存 {len(items)} 道题", "success")
    if skipped:
        reporter.log(
            "下面这些题一屏放不下、被跳过了，需要手动补截："
            + "、".join(str(number) for number in skipped),
            "warn",
        )


def summary_paper(
    reporter: Reporter, total: int, counts: dict[str, int], skipped: Sequence[str]
) -> None:
    """整卷采集结束汇报。"""

    reporter.log(f"本次共保存 {total} 道题", "success")
    for label, count in counts.items():
        reporter.log(f"    {label} {count} 道", "info")
    if skipped:
        reporter.log(
            "下面这些题一屏放不下、被跳过了，需要手动补截：" + "、".join(skipped),
            "warn",
        )


def unique_types(value: str) -> tuple[str, ...]:
    """把设置里的题型列表解析成元组（给动作层复用）。"""

    return split_list(value, ())
