# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: PyInstaller 打包脚本（onedir）                        #
# ================================================================== #
# 用法：
#   .venv\Scripts\pyinstaller packaging\Sciyardcampus_Kit.spec --noconfirm
# 产物：
#   dist\Sciyardcampus_Kit\Sciyardcampus_Kit.exe
#
# 注意：
#   - web/dist 必须先 npm run build；spec 只负责把它一起带进包；
#   - pywebview 的 Windows 后端是运行时按名字加载的，静态分析看不到，
#     必须显式列 hiddenimports。

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).parent  # noqa: F821 - SPECPATH 由 PyInstaller 注入

# 前端构建产物、图标/版本号等只读资源
datas = [
    (str(ROOT / "web" / "dist"), "web/dist"),
    (str(ROOT / "resources"), "resources"),
]
# pywebview 自带 JS 注入文件，必须一起打包
datas += collect_data_files("webview")

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    # Windows WebView2 后端 + pythonnet/clr_loader 都是动态加载
    hiddenimports=[
        "webview.platforms.edgechromium",
        "clr_loader",
        "pythonnet",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 这些库本项目用不到，排除后能明显减小体积
    excludes=[
        "tkinter",
        "matplotlib",
        "pandas",
        "scipy",
        "IPython",
        "pytest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Sciyardcampus_Kit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # 桌面 GUI：不弹控制台窗口
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "resources" / "images" / "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Sciyardcampus_Kit",
)
