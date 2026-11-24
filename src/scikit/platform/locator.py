# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 数据目录解析：命令行/环境变量/便携/用户选择/默认        #
# ================================================================== #
# 优先级：CLI/环境变量 → portable.json → 用户上次选择 → 默认应用目录
#        → AppData 兜底。
# 默认应用目录：源码运行时是仓库根，打包后是 exe 所在目录。
# 只做路径决策与可写性探测，不负责配置内容读写（那是 store.py 的事）。

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from scikit import const
from scikit.errors import AppError
from scikit.paths import app_dir, appdata_dir


@dataclass
class Location:
    """一次解析的结果：最终目录 + 来源 + 是否便携 + 是否可写 + 提示。"""

    path: Path
    source: str  # cli | env | portable | user | default | fallback
    portable: bool = False
    writable: bool = True
    note: str = ""

    def to_dict(self) -> dict:
        """转成前端“存储位置”面板要的 JSON。"""

        return {
            "path": str(self.path),
            "source": self.source,
            "portable": self.portable,
            "writable": self.writable,
            "note": self.note,
        }


def _probe(directory: Path) -> bool:
    """真写一个临时文件来确认目录可写（只看 exists 不够）。"""

    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / const.WRITE_PROBE_FILE
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except Exception:  # noqa: BLE001 - 任何失败都视为不可写
        return False


def _read_json(path: Path) -> dict:
    """读 JSON；文件缺失、损坏或顶层不是对象时返回空字典。"""

    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _write_json(path: Path, data: dict) -> None:
    """原子写 JSON：先写 .tmp 再替换。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def portable_file() -> Path:
    """便携标记文件路径（应用目录下的 portable.json）。"""

    return app_dir() / const.PORTABLE_FILE


def user_pointer_file() -> Path:
    """用户级“上次选过的数据目录”指针（AppData 下）。"""

    return appdata_dir() / const.LOCATION_POINTER_FILE


def default_dir() -> Path:
    """
    默认数据目录 = 应用目录。

    - 源码运行：仓库根目录 → 产物在 <仓库>/resources/，与上游一致；
    - 打包运行：exe 所在目录 → 产物在 <exe>/resources/，配置在 <exe>/.scikit/。

    用户仍可在设置里把数据目录改到别处。
    """

    return app_dir()


def fallback_dir() -> Path:
    """兜底数据目录：AppData 下，应用目录不可写时使用。"""

    return appdata_dir() / const.FALLBACK_DATA_DIR_NAME


def _candidate(cli_dir: str | None) -> tuple[Path, str, bool, str]:
    """按优先级挑候选目录；只负责选，不保证可写。"""

    if cli_dir:
        return Path(cli_dir).expanduser(), "cli", False, ""
    env_dir = os.environ.get(const.DATA_ENV_VAR)
    if env_dir:
        return Path(env_dir).expanduser(), "env", False, ""

    portable_path = portable_file()
    if portable_path.exists():
        raw = _read_json(portable_path).get("dataDir")
        target = Path(raw).expanduser() if raw else default_dir()
        # 相对路径按 exe 所在目录解析，便于整包搬动
        if not target.is_absolute():
            target = app_dir() / target
        return target, "portable", True, ""

    pointer = user_pointer_file()
    if pointer.exists():
        raw = _read_json(pointer).get("dataDir")
        if raw:
            return Path(raw).expanduser(), "user", False, ""

    return default_dir(), "default", False, ""


def resolve(cli_dir: str | None = None) -> Location:
    """解析出真正可用的数据目录；不可写时自动回退到 AppData。"""

    path, source, portable, note = _candidate(cli_dir)
    if _probe(path):
        return Location(path=path, source=source, portable=portable, note=note)

    fallback = fallback_dir()
    if _probe(fallback):
        return Location(
            path=fallback,
            source="fallback",
            portable=False,
            writable=True,
            note=f"数据目录 {path} 不可写，已改用 {fallback}",
        )
    raise AppError(
        "STORAGE_UNWRITABLE",
        "没有可写入的数据目录",
        f"尝试过：{path} 与 {fallback}",
    )


def set_user_location(path: Path) -> None:
    """记住用户选中的数据目录。"""

    _write_json(user_pointer_file(), {"dataDir": str(path)})


def clear_user_location() -> None:
    """清除用户选择，下次启动回到默认目录。"""

    try:
        user_pointer_file().unlink()
    except FileNotFoundError:
        pass


def set_portable(path: Path) -> None:
    """把数据目录写进 portable.json；写失败转成 AppError。"""

    try:
        _write_json(portable_file(), {"dataDir": str(path)})
    except Exception as error:  # noqa: BLE001
        raise AppError("PORTABLE_WRITE_FAILED", "无法写入 portable.json", str(error)) from error
