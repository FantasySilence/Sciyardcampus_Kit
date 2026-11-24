# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 程序入口：把 src/ 加进模块搜索路径后启动应用            #
# ================================================================== #

from __future__ import annotations

import os
import sys

# 源码运行时 Python 找不到 src/scikit，这里手动把 <仓库>/src 放到搜索路径最前面；
# 打包后 scikit 已经收进 exe，这行只是多了一个无效路径，不会影响运行。
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from scikit.app import run  # noqa: E402

if __name__ == "__main__":
    run()
