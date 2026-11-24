# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 检查会话：采集结果的持久化清单（预览与导出的唯一数据源）#
# ================================================================== #
# 为什么需要 session：
#   - 采集完不直接导出，中间还要让用户预览、剔除；
#   - 关掉应用再打开，检查进度不能丢；
#   - 导出必须严格等于预览里勾选的内容，不能重新扫目录。
# 文件放在 <data>/.scikit/sessions/<id>.json，索引按目录扫描，避免索引损坏。

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from scikit import const
from scikit.errors import AppError
from scikit.pipeline import library
from scikit.pipeline.defaults import Tuning as _TuningCls

# 会话统计只需要标签顺序；用一个固定 Tuning 即可
_TUNING = _TuningCls()


class SessionStore:
    """一个数据目录下的检查会话仓储。"""

    def __init__(self, sessions_dir: str | Path) -> None:
        self.root = Path(sessions_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    # ------ 创建 / 读取 ------ #
    def create(self, scope: dict, items: list[dict], source: str = "capture") -> dict:
        """新建会话：补齐条目字段、算统计、落盘。"""

        now = _now()
        session = {
            "id": uuid.uuid4().hex[:12],
            "createdAt": now,
            "updatedAt": now,
            "source": source,
            "scope": dict(scope),
            "items": [_normalize(item, position) for position, item in enumerate(items, 1)],
            "stats": {},
        }
        session["stats"] = library.stats_for_items(session["items"], _TUNING)
        self.save(session)
        return session

    def load(self, session_id: str) -> dict:
        """按 id 读取；id 非法或文件缺失都抛 SESSION_NOT_FOUND。"""

        path = self._path(session_id)
        data = _read_json(path)
        if data is None:
            raise AppError("SESSION_NOT_FOUND", "检查会话不存在或已损坏", str(path))
        # 旧会话可能没有 exportMode 等新字段，读出来时统一补齐
        data["items"] = [
            _normalize(item, position)
            for position, item in enumerate(data.get("items", []), 1)
        ]
        return data

    def save(self, session: dict) -> dict:
        """原子写入会话；同时刷新 updatedAt 与统计。"""

        session["updatedAt"] = _now()
        session["stats"] = library.stats_for_items(session.get("items", []), _TUNING)
        path = self._path(session["id"])
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as file:
            json.dump(session, file, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return session

    # ------ 更新 ------ #
    def update_included(self, session_id: str, included: dict) -> dict:
        """更新勾选状态：{题号: true/false}，只认会话里存在的条目。"""

        session = self.load(session_id)
        mapping = {int(key): bool(value) for key, value in (included or {}).items()}
        for item in session.get("items", []):
            index = int(item.get("index", 0))
            if index in mapping:
                item["included"] = mapping[index]
        return self.save(session)

    def update_items(self, session_id: str, changed: list[dict]) -> dict:
        """按 index 合并条目字段（重新识别后更新 tags/txt/ocrError）。"""

        session = self.load(session_id)
        patch = {int(item["index"]): item for item in changed if "index" in item}
        for item in session.get("items", []):
            update = patch.get(int(item.get("index", 0)))
            if not update:
                continue
            for key in (
                "tags",
                "txt",
                "ocrError",
                "number",
                "kind",
                "exportMode",
            ):
                if key in update:
                    item[key] = update[key]
        return self.save(session)

    def set_render_mode(self, session_id: str, index: int, mode: str) -> dict:
        """设置某题在 Word 里用文字还是图片（auto/text/image）。"""

        if mode not in const.EXPORT_MODES:
            raise AppError("INVALID_INPUT", f"不支持的导出模式：{mode}")
        session = self.load(session_id)
        for item in session.get("items", []):
            if int(item.get("index", 0)) == int(index):
                item["exportMode"] = mode
                return self.save(session)
        raise AppError("ITEM_NOT_FOUND", "会话里没有这道题", str(index))

    def set_all_render_mode(self, session_id: str, mode: str) -> dict:
        """一键把整卷所有题设成同一种呈现方式（text/image）。"""

        if mode not in const.EXPORT_MODES:
            raise AppError("INVALID_INPUT", f"不支持的导出模式：{mode}")
        session = self.load(session_id)
        items = session.get("items", [])
        if not items:
            raise AppError("SESSION_EMPTY", "这个会话里没有题目")
        for item in items:
            item["exportMode"] = mode
        return self.save(session)

    # ------ 列表 ------ #
    def list(self) -> list[dict]:
        """扫描所有会话文件，返回摘要（损坏文件跳过）。"""

        sessions: list[dict] = []
        for path in sorted(self.root.glob("*.json")):
            data = _read_json(path)
            if data is None or "id" not in data:
                continue
            data["items"] = [
                _normalize(item, position)
                for position, item in enumerate(data.get("items", []), 1)
            ]
            sessions.append(data)
        sessions.sort(key=lambda item: item.get("updatedAt", ""), reverse=True)
        return sessions

    def latest_for_scope(self, scope: dict) -> dict | None:
        """找同一范围最新的会话；历史面板合成条目时用。"""

        key = library.scope_key(scope)
        matches = [
            item
            for item in self.list()
            if library.scope_key(item.get("scope", {})) == key
        ]
        return matches[0] if matches else None

    # ------ 内部 ------ #
    def _path(self, session_id: str) -> Path:
        """校验 id 只含十六进制字符，防止路径穿越。"""

        value = str(session_id or "").strip()
        if not value or not all(char in "0123456789abcdef" for char in value.lower()):
            raise AppError("INVALID_SESSION", "会话 id 无效", value)
        return self.root / f"{value}.json"


def _now() -> str:
    """本地时间 ISO 字符串（微秒级，保证同一秒内多次保存也能正确排序）。"""

    return datetime.now().isoformat(timespec="microseconds")


def _normalize(item: dict, position: int) -> dict:
    """补齐条目必备字段，避免旧会话/手写 JSON 缺键导致前端报错。"""

    index = int(item.get("index") or position)
    return {
        "index": index,
        "number": item.get("number", index),
        "kind": item.get("kind", "未知"),
        "png": item.get("png", ""),
        "txt": item.get("txt", ""),
        "tags": list(item.get("tags") or []),
        "included": bool(item.get("included", True)),
        "exportMode": _mode(item.get("exportMode")),
        "ocrError": item.get("ocrError", ""),
    }


def _mode(value: object) -> str:
    """校验会话里的导出模式；旧数据缺字段时回落到 auto。"""

    mode = str(value or const.DEFAULT_EXPORT_MODE)
    return mode if mode in const.EXPORT_MODES else const.DEFAULT_EXPORT_MODE


def _read_json(path: Path) -> dict | None:
    """读 JSON；不存在/损坏/顶层不是对象时返回 None。"""

    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001 - 损坏会话只跳过
        return None
