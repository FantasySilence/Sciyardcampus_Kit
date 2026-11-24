# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 默认数据根与目录布局测试                               #
# ================================================================== #

from __future__ import annotations

from scikit import const
from scikit.paths import app_dir
from scikit.pipeline.artifact_paths import ArtifactPaths
from scikit.platform import locator


def test_default_root_is_app_dir() -> None:
    """源码运行时默认数据根是仓库根，打包后是 exe 目录。"""

    assert locator.default_dir() == app_dir()


def test_default_layout_matches_upstream() -> None:
    """产物在 resources/，应用私有文件在 .scikit/。"""

    paths = ArtifactPaths(locator.default_dir())
    assert paths.resources_dir == app_dir() / const.RESOURCES_DIR_NAME
    assert paths.row_pngs_dir == paths.resources_dir / const.ROW_PNGS_DIR_NAME
    assert paths.word_output_dir == paths.resources_dir / const.WORD_OUTPUT_DIR_NAME
    assert paths.scikit_dir == app_dir() / const.SCIKIT_DIR_NAME
    assert paths.settings_dir == paths.scikit_dir / const.SETTINGS_SUBDIR


def test_custom_root_moves_everything(tmp_path) -> None:
    """设置里换数据根后，resources 与 .scikit 一起搬到新目录。"""

    paths = ArtifactPaths(tmp_path)
    assert paths.resources_dir == tmp_path / const.RESOURCES_DIR_NAME
    assert paths.scikit_dir == tmp_path / const.SCIKIT_DIR_NAME
