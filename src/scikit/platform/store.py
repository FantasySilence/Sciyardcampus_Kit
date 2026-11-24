# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 配置仓储：JSON 原子写、自动备份、损坏恢复              #
# ================================================================== #
# 上层只用 load / save；当前配置放 settings/，历史副本放 backups/。

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from scikit import const


class Store:
    """一个数据目录的配置仓储：<root>/settings 存配置，<root>/backups 存副本。"""

    def __init__(self, root: Path) -> None:
        """记录根目录，并确保 settings/ 与 backups/ 存在。"""

        self.root = Path(root)
        self.settings_dir = self.root / const.SETTINGS_SUBDIR
        self.backup_dir = self.root / const.BACKUPS_SUBDIR
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    # ------ 路径 ------ #
    def path(self, name: str) -> Path:
        """配置名 → 完整路径；name 不带后缀。"""

        return self.settings_dir / f"{name}.json"

    # ------ 读写 ------ #
    def load(self, name: str, default: dict | None = None) -> dict:
        """读取配置：主文件可用就用它；损坏或缺失时尝试最新备份。"""

        default = default or {}
        path = self.path(name)
        data = self._read(path)
        if data is not None:
            return data
        restored = self._restore(name)
        if restored is not None:
            return restored
        return dict(default)

    def save(self, name: str, data: dict) -> dict:
        """保存配置：先备份旧文件，再写临时文件并原子替换。"""

        path = self.path(name)
        self._snapshot(name, path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        # 同分区上 os.replace 是原子操作，不会留下半个文件
        os.replace(tmp, path)
        return data

    def export_all(self) -> dict[str, Any]:
        """把所有 *.json 配置汇总成 {名称: 内容}。"""

        result: dict[str, Any] = {}
        for file in sorted(self.settings_dir.glob("*.json")):
            try:
                with open(file, encoding="utf-8") as stream:
                    result[file.stem] = json.load(stream)
            except Exception:  # noqa: BLE001 - 单个坏文件只跳过
                continue
        return result

    # ------ 内部 ------ #
    @staticmethod
    def _read(path: Path) -> dict | None:
        """读一个 JSON；不存在、解析失败或顶层不是对象时返回 None。"""

        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, dict) else None
        except Exception:  # noqa: BLE001 - 损坏时交给备份
            return None

    def _snapshot(self, name: str, path: Path) -> None:
        """写前备份：复制到 backups/，只保留最近 const.STORE_MAX_BACKUPS 份。"""

        if not path.exists():
            return
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target = self.backup_dir / f"{name}.{stamp}.json"
        try:
            shutil.copy2(path, target)
        except Exception:  # noqa: BLE001 - 备份失败不影响主流程
            return
        backups = sorted(self.backup_dir.glob(f"{name}.*.json"))
        for old in backups[: -const.STORE_MAX_BACKUPS]:
            try:
                old.unlink()
            except OSError:
                pass

    def _restore(self, name: str) -> dict | None:
        """从最新可用备份恢复，并写回主文件。"""

        backups = sorted(self.backup_dir.glob(f"{name}.*.json"), reverse=True)
        for backup in backups:
            data = self._read(backup)
            if data is not None:
                try:
                    shutil.copy2(backup, self.path(name))
                except OSError:
                    pass
                return data
        return None
