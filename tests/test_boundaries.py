# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 架构边界测试：工具互不 import、流水线不碰 WebView       #
# ================================================================== #

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "scikit"


def iter_python(folder: Path):
    yield from folder.rglob("*.py")


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def test_tools_do_not_import_each_other() -> None:
    for tool_dir in (SRC / "tools").iterdir():
        if not tool_dir.is_dir() or tool_dir.name.startswith("__"):
            continue
        for file in iter_python(tool_dir):
            for module in imported_modules(file):
                if not module.startswith("scikit.tools."):
                    continue
                other = module.split(".")[2]
                assert other == tool_dir.name, f"{file} imports {module}"


def test_pipeline_does_not_import_webview() -> None:
    for file in iter_python(SRC / "pipeline"):
        for module in imported_modules(file):
            assert module.split(".")[0] != "webview", f"{file} imports webview"


def test_pipeline_has_no_print_calls() -> None:
    for file in iter_python(SRC / "pipeline"):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "print", f"{file} still uses print()"
