# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 采集导出工具的动作：预检、采集、会话、重识别、导出      #
# ================================================================== #
# 约定：
#   - 长任务只创建 job 并返回 jobId，不在这里阻塞；
#   - 参数校验同步做，错误立刻以 AppError 返回；
#   - 采集任务内部先落 session 再 OCR，OCR 失败也不丢采集结果。

from __future__ import annotations

from scikit import const
from scikit.device import create_device
from scikit.device.mouse import MouseDevice
from scikit.errors import AppError
from scikit.pipeline import capture, docx, extract, library
from scikit.pipeline.defaults import Tuning
from scikit.pipeline.ocr import TesseractOcr
from scikit.platform import params
from scikit.platform.schema import get_path


# ================================================================== #
# @Description: 公共工具函数                                           #
# ================================================================== #
def _settings(ctx) -> dict:
    """读取本工具当前设置（已按 schema 清洗）。"""

    return ctx.settings("export")


def _tuning(settings: dict) -> Tuning:
    """从设置生成不可变参数对象。"""

    return Tuning.from_settings(settings)


def _ocr(settings: dict, tuning: Tuning, paths) -> TesseractOcr:
    """按设置创建 OCR 客户端。"""

    return TesseractOcr(
        str(get_path(settings, "ocr.tesseractPath", "") or ""),
        paths.tmp_dir,
        timeout=tuning.ocr_timeout,
    )


def _scope(payload: dict, paths) -> dict:
    """校验并生成范围：整卷用 paper，单题型用 pngType。"""

    mode = params.choice(payload, "mode", ("paper", "type"), default="paper")
    if mode == "paper":
        paper = params.text(payload, "paper")
        if not paper:
            raise AppError("INVALID_INPUT", "请填写卷名")
        return {"mode": "paper", "paper": paths.safe_name(paper, "卷名")}
    png_type = params.text(payload, "pngType")
    if not png_type:
        raise AppError("INVALID_INPUT", "请选择题型")
    return {"mode": "type", "pngType": paths.safe_name(png_type, "题型")}


def _minimize_if_mouse(ctx, device, reporter) -> bool:
    """鼠标通道时最小化应用窗口并给用户切换时间；返回是否需要恢复。"""

    if not isinstance(device, MouseDevice):
        return False
    window = getattr(ctx.runtime, "window", None)
    if window is None:
        return False
    try:
        window.minimize()
        reporter.log("已最小化应用窗口；请让模拟器保持可见", "warn")
        reporter.sleep(2.0)
    except Exception as error:  # noqa: BLE001 - 最小化失败不阻塞采集
        reporter.log(f"最小化窗口失败：{error}", "warn")
    return True


def _restore_window(ctx, needed: bool) -> None:
    """采集结束后恢复应用窗口。"""

    if not needed:
        return
    window = getattr(ctx.runtime, "window", None)
    if window is None:
        return
    try:
        window.restore()
    except Exception:  # noqa: BLE001
        pass


def _public_session(ctx, session: dict) -> dict:
    """给前端补上 OCR 文字与展示字段。"""

    items = []
    for item in session.get("items", []):
        data = dict(item)
        data["text"] = library.read_item_text(ctx.paths, item)
        items.append(data)
    scope = session.get("scope", {})
    tuning = _tuning(_settings(ctx))
    return {
        "session": {**session, "items": items},
        "title": library.scope_title(scope),
        "docxName": docx.default_filename(scope, tuning),
        "stats": library.stats_for_items(items, tuning),
    }


def _load_session(ctx, session_id: str) -> dict:
    """按 id 读取会话；同时刷新统计。"""

    session = ctx.sessions.load(session_id)
    session["stats"] = library.stats_for_items(session.get("items", []), _tuning(_settings(ctx)))
    return session


def _session_from_scope(ctx, scope: dict) -> dict:
    """
    按范围取会话。

    - 有已保存 session：以磁盘为准重建条目（能带出新加的图片），
      同时沿用 session 里的勾选/剔除状态；
    - 没有 session（旧产物）：现场建一个 source=files 的会话，
      这样预览页的剔除、重识别、导出都能正常工作。
    """

    tuning = _tuning(_settings(ctx))
    saved = ctx.sessions.latest_for_scope(scope)
    items = library.build_items_from_files(ctx.paths, scope, tuning, saved=saved)
    if not items:
        raise AppError("SESSION_EMPTY", "这个范围里还没有可预览的题目")

    if saved is not None:
        session = dict(saved)
        session["items"] = items
        session["stats"] = library.stats_for_items(items, tuning)
        # 把新补进来的图片/勾选状态一起写回，避免下一次更新时丢失
        return ctx.sessions.save(session)

    return ctx.sessions.create(scope, items, source="files")


# ================================================================== #
# @Description: 预检                                                   #
# ================================================================== #
def probe_action(payload: dict, ctx) -> dict:
    """创建预检任务：截一屏，返回识别框和题号。"""

    settings = _settings(ctx)
    tuning = _tuning(settings)
    paths = ctx.paths

    def run(job, reporter) -> dict:
        device = create_device(settings, tuning, reporter)
        minimized = _minimize_if_mouse(ctx, device, reporter)
        try:
            ocr = _ocr(settings, tuning, paths)
            result = capture.probe(device, ocr, paths, tuning, reporter)
            result["channel"] = device.describe()
            return result
        finally:
            _restore_window(ctx, minimized)

    job_id = ctx.jobs.start("probe", "预检当前画面", run)
    return {"jobId": job_id}


# ================================================================== #
# @Description: 采集（采集 + 自动 OCR + 落 session）                    #
# ================================================================== #
def start_capture_action(payload: dict, ctx) -> dict:
    """创建采集任务：按范围采集，采集完落 session，再自动 OCR。"""

    settings = _settings(ctx)
    tuning = _tuning(settings)
    paths = ctx.paths
    scope = _scope(payload, paths)
    pages = params.integer(
        payload,
        "pages",
        default=int(
            get_path(settings, "capture.pages", const.DEFAULT_TUNING["pages"])
        ),
        minimum=const.CAPTURE_PAGES_MIN,
        maximum=const.CAPTURE_PAGES_MAX,
        label="题量上限",
    )
    clear_old = params.boolean(payload, "clearOld", default=False)

    title = f"采集 {library.scope_title(scope)}"

    def run(job, reporter) -> dict:
        device = create_device(settings, tuning, reporter)
        minimized = _minimize_if_mouse(ctx, device, reporter)
        try:
            ocr = _ocr(settings, tuning, paths)
            if scope["mode"] == "paper":
                items = capture.capture_paper(
                    device, paths, scope["paper"], pages, ocr, reporter, tuning
                )
            else:
                items = capture.capture_type(
                    device,
                    paths,
                    scope["pngType"],
                    pages,
                    ocr,
                    reporter,
                    tuning,
                    clear_old=clear_old,
                )

            if not items:
                raise AppError("NOTHING_CAPTURED", "本次没有采集到题目")

            # 先落 session：OCR 中途失败也不会丢采集结果
            session = ctx.sessions.create(scope, items)
            reporter.log(f"采集完成，共 {len(items)} 题，开始识别文字", "success")

            ocr_stats = None
            ocr_error = ""
            try:
                ocr_stats = extract.extract_items(
                    paths, scope, items, ocr, reporter, tuning
                )
            except AppError as error:
                ocr_error = error.message
                reporter.log(f"文字识别失败：{error.message}；采集结果已保留", "error")
            finally:
                ctx.sessions.update_items(session["id"], items)

            return {
                "sessionId": session["id"],
                "captured": len(items),
                "ocr": ocr_stats,
                "ocrError": ocr_error,
            }
        finally:
            _restore_window(ctx, minimized)

    job_id = ctx.jobs.start("capture", title, run, payload={"scope": scope, "pages": pages})
    return {"jobId": job_id, "scope": scope}


# ================================================================== #
# @Description: 会话读取 / 更新                                        #
# ================================================================== #
def session_get_action(payload: dict, ctx) -> dict:
    """按 sessionId 或 scope 取会话，附带文字与统计。"""

    session_id = params.text(payload, "sessionId")
    if session_id:
        session = _load_session(ctx, session_id)
    else:
        session = _session_from_scope(ctx, _scope(payload, ctx.paths))
    return _public_session(ctx, session)


def session_update_action(payload: dict, ctx) -> dict:
    """更新勾选状态（剔除/恢复）。"""

    session_id = params.text(payload, "sessionId")
    if not session_id:
        raise AppError("INVALID_INPUT", "缺少会话 id")
    included = params.obj(payload, "included")
    session = ctx.sessions.update_included(session_id, included)
    tuning = _tuning(_settings(ctx))
    return {
        "sessionId": session["id"],
        "stats": library.stats_for_items(session.get("items", []), tuning),
    }


def _find_item(session: dict, index: int) -> dict:
    """在会话里按题号找条目；找不到抛 ITEM_NOT_FOUND。"""

    for item in session.get("items", []):
        if int(item.get("index", 0)) == int(index):
            return item
    raise AppError("ITEM_NOT_FOUND", "会话里没有这道题", str(index))


def save_text_action(payload: dict, ctx) -> dict:
    """
    把预览里编辑过的文字写回该题的 txt，并刷新会话。

    - 已有 txt：覆盖原文件（保留原标签后缀）；
    - 没有 txt：按标签生成新文件名（如 3_formula.txt）；
    - 编辑后清掉 ocrError，表示这题已经有可用的文字。
    """

    session_id = params.text(payload, "sessionId")
    if not session_id:
        raise AppError("INVALID_INPUT", "缺少会话 id")
    index = params.integer(payload, "index", minimum=1, label="题号")
    raw = payload.get("text")
    if not isinstance(raw, str):
        raise AppError("INVALID_INPUT", "text 必须是字符串")
    if len(raw) > const.MAX_TEXT_EDIT_LENGTH:
        raise AppError(
            "TEXT_TOO_LARGE",
            "这道题的文字太长",
            f"最多 {const.MAX_TEXT_EDIT_LENGTH} 字",
        )

    session = _load_session(ctx, session_id)
    item = _find_item(session, index)
    tuning = _tuning(_settings(ctx))
    scope = session.get("scope", {})

    if item.get("txt"):
        target = ctx.paths.resolve_rel(item["txt"])
    else:
        suffix = "".join(
            tuning.ocr_kind_suffix[kind]
            for kind in tuning.ocr_kind_order
            if kind in item.get("tags", [])
        )
        if scope.get("mode") == "paper":
            target = ctx.paths.paper_txt_path(scope["paper"], index, suffix)
        else:
            target = ctx.paths.txt_path(scope["pngType"], index, suffix)

    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text.rstrip("\n") + "\n", encoding="utf-8")
    except OSError as error:
        raise AppError("WRITE_FAILED", "无法写入 txt", str(error)) from error

    item["txt"] = ctx.paths.rel(target)
    item["ocrError"] = ""
    ctx.sessions.update_items(session_id, [item])
    return _public_session(ctx, ctx.sessions.load(session_id))


def set_render_mode_action(payload: dict, ctx) -> dict:
    """设置某题导出 Word 时用文字还是图片（auto/text/image）。"""

    session_id = params.text(payload, "sessionId")
    if not session_id:
        raise AppError("INVALID_INPUT", "缺少会话 id")
    index = params.integer(payload, "index", minimum=1, label="题号")
    mode = params.choice(payload, "mode", const.EXPORT_MODES)
    ctx.sessions.set_render_mode(session_id, index, mode)
    return _public_session(ctx, ctx.sessions.load(session_id))


# ================================================================== #
# @Description: 单题/批量重新识别                                      #
# ================================================================== #
def start_ocr_action(payload: dict, ctx) -> dict:
    """对会话里指定题重新识别；不传 indexes 则识别全部。"""

    session_id = params.text(payload, "sessionId")
    if not session_id:
        raise AppError("INVALID_INPUT", "缺少会话 id")
    raw_indexes = payload.get("indexes") or []
    if not isinstance(raw_indexes, list):
        raise AppError("INVALID_INPUT", "indexes 必须是数组")
    indexes = [int(value) for value in raw_indexes]

    session = _load_session(ctx, session_id)
    settings = _settings(ctx)
    tuning = _tuning(settings)
    scope = session.get("scope", {})

    def run(job, reporter) -> dict:
        ocr = _ocr(settings, tuning, ctx.paths)
        stats = extract.extract_items(
            ctx.paths,
            scope,
            session.get("items", []),
            ocr,
            reporter,
            tuning,
            indexes=indexes or None,
        )
        ctx.sessions.update_items(session["id"], session.get("items", []))
        return {"sessionId": session["id"], "stats": stats}

    title = "重新识别" if indexes else "识别全部文字"
    return {"jobId": ctx.jobs.start("ocr", title, run)}


# ================================================================== #
# @Description: 导出 Word                                              #
# ================================================================== #
def start_export_action(payload: dict, ctx) -> dict:
    """按会话里勾选的题生成 Word。"""

    session_id = params.text(payload, "sessionId")
    if not session_id:
        raise AppError("INVALID_INPUT", "缺少会话 id")
    session = _load_session(ctx, session_id)
    tuning = _tuning(_settings(ctx))
    scope = session.get("scope", {})
    filename = params.text(payload, "filename") or docx.default_filename(scope, tuning)
    filename = ctx.paths.safe_filename(filename)
    overwrite = params.boolean(payload, "overwrite", default=False)

    target = ctx.paths.word_path(filename)
    if target.exists() and not overwrite:
        raise AppError("FILE_EXISTS", "同名 Word 已存在", target.name)

    items = session.get("items", [])

    def run(job, reporter) -> dict:
        return docx.build(
            ctx.paths, scope, items, filename, tuning, reporter, overwrite=True
        )

    title = f"导出 {filename}"
    return {"jobId": ctx.jobs.start("export", title, run)}


# ================================================================== #
# @Description: 历史                                                   #
# ================================================================== #
def history_action(payload: dict, ctx) -> dict:
    """返回历史会话 + 只有文件的旧产物 + 目录清单。"""

    tuning = _tuning(_settings(ctx))
    sessions = ctx.sessions.list()
    entries = library.history(ctx.paths, tuning, sessions)
    return {
        "entries": entries,
        "inventory": library.inventory(ctx.paths, tuning),
    }
