# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 任务系统测试：进度、日志、取消、单任务互斥             #
# ================================================================== #

from __future__ import annotations

import threading
import time

import pytest

from scikit.errors import AppError
from scikit.jobs import JobManager


def wait_status(manager: JobManager, job_id: str, timeout: float = 5.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        snapshot = manager.status(job_id)
        if snapshot["status"] != "running":
            return snapshot
        time.sleep(0.01)
    raise AssertionError("任务超时")


def test_job_reports_progress_and_logs() -> None:
    manager = JobManager()

    def work(job, reporter) -> dict:
        for index in range(3):
            reporter.progress(index, 3, f"step {index}", "test")
            reporter.log(f"line {index}")
        reporter.progress(3, 3, "done", "test")
        return {"value": 42}

    job_id = manager.start("test", "demo", work)
    snapshot = wait_status(manager, job_id)

    assert snapshot["status"] == "done"
    assert snapshot["result"] == {"value": 42}
    assert snapshot["progress"]["current"] == 3
    assert len(snapshot["logs"]) >= 4
    assert snapshot["logs"][-1]["text"] == "任务完成"


def test_cancel_stops_cooperatively() -> None:
    manager = JobManager()

    def work(job, reporter) -> dict:
        while True:
            reporter.check()
            reporter.sleep(0.02)

    job_id = manager.start("test", "long", work)
    time.sleep(0.05)
    assert manager.cancel(job_id) is True
    snapshot = wait_status(manager, job_id)

    assert snapshot["status"] == "cancelled"


def test_only_one_job_at_a_time() -> None:
    manager = JobManager()
    gate = threading.Event()

    def work(job, reporter) -> dict:
        gate.wait(2)
        return {}

    first = manager.start("test", "first", work)
    with pytest.raises(AppError) as error:
        manager.start("test", "second", work)
    assert error.value.code == "JOB_BUSY"

    gate.set()
    wait_status(manager, first)


def test_unknown_job_id() -> None:
    manager = JobManager()
    with pytest.raises(AppError) as error:
        manager.status("not-exist")
    assert error.value.code == "JOB_NOT_FOUND"
