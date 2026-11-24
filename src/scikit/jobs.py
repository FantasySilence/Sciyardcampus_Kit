# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 后台任务：状态、增量日志、进度、协作式取消              #
# ================================================================== #
# 为什么需要它：一次采集/OCR 可能跑几分钟，不能塞进一次 pywebview 调用。
# 约定：
#   - 工具动作只负责创建任务并立刻返回 jobId；
#   - 前端每 500ms 调 job_status(jobId, since) 拿增量日志；
#   - 任务线程通过 Reporter 汇报，退出前一定落终态。

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from scikit import const
from scikit.errors import AppError


class JobCancelled(Exception):
    """任务被用户取消：由 Reporter.check()/sleep() 抛出，JobManager 转成 cancelled。"""


@dataclass
class Job:
    """一个后台任务的完整状态；所有字段都在 Job 的锁内读写。"""

    id: str
    kind: str
    title: str
    payload: dict
    status: str = "running"  # running | done | failed | cancelled
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    ended_at: float | None = None
    progress: dict = field(
        default_factory=lambda: {"current": 0, "total": None, "label": "", "phase": ""}
    )
    logs: deque = field(
        default_factory=lambda: deque(maxlen=const.JOB_MAX_LOGS)
    )
    artifacts: deque = field(
        default_factory=lambda: deque(maxlen=const.JOB_MAX_ARTIFACTS)
    )
    result: Any = None
    error: dict | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    done_event: threading.Event = field(default_factory=threading.Event)
    lock: threading.RLock = field(default_factory=threading.RLock)
    seq: int = 0

    def log(self, text: str, level: str = "info") -> None:
        """追加一条日志；seq 单调递增，前端按 since 取增量。"""

        with self.lock:
            self.seq += 1
            self.logs.append(
                {
                    "seq": self.seq,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "level": level,
                    "text": text,
                }
            )

    def set_progress(
        self,
        current: int,
        total: int | None = None,
        label: str | None = None,
        phase: str | None = None,
    ) -> None:
        """更新进度；total=None 表示总量未知（前端显示不确定进度条）。"""

        with self.lock:
            self.progress["current"] = int(current)
            if total is not None:
                self.progress["total"] = int(total)
            if label is not None:
                self.progress["label"] = str(label)
            if phase is not None:
                self.progress["phase"] = str(phase)

    def add_artifact(self, path: str, meta: dict | None = None) -> None:
        """记录一个最近产物（相对数据根），供前端显示缩略图。"""

        with self.lock:
            self.artifacts.append({"path": str(path), "meta": dict(meta or {})})

    def snapshot(self, since: int = 0) -> dict:
        """生成给前端的状态快照；只返回 since 之后的日志。"""

        with self.lock:
            logs = [entry for entry in self.logs if entry["seq"] > since]
            return {
                "id": self.id,
                "kind": self.kind,
                "title": self.title,
                "status": self.status,
                "progress": dict(self.progress),
                "logs": logs,
                "artifacts": list(self.artifacts),
                "result": self.result,
                "error": self.error,
                "createdAt": self.created_at,
                "startedAt": self.started_at,
                "endedAt": self.ended_at,
                "elapsed": round((self.ended_at or time.time()) - self.created_at, 1),
            }


class Reporter:
    """任务线程持有的汇报器：日志、进度、产物、取消检查。"""

    def __init__(self, job: Job) -> None:
        self._job = job

    @property
    def cancelled(self) -> bool:
        """用户是否已请求取消。"""

        return self._job.cancel_event.is_set()

    def log(self, text: str, level: str = "info") -> None:
        """写一条日志（分 info / warn / error / success）。"""

        self._job.log(text, level)

    def progress(
        self,
        current: int,
        total: int | None = None,
        label: str | None = None,
        phase: str | None = None,
    ) -> None:
        """更新进度；阶段变化时前端会切换标题。"""

        self._job.set_progress(current, total, label, phase)

    def artifact(self, path: str, meta: dict | None = None) -> None:
        """记录最近产物。"""

        self._job.add_artifact(path, meta)

    def check(self) -> None:
        """取消检查点：每个循环迭代都要调一次。"""

        if self._job.cancel_event.is_set():
            raise JobCancelled("任务已取消")

    def sleep(self, seconds: float) -> None:
        """可被取消打断的等待，替代 time.sleep。"""

        if seconds <= 0:
            self.check()
            return
        if self._job.cancel_event.wait(seconds):
            raise JobCancelled("任务已取消")


class JobManager:
    """任务管理器：单任务互斥、线程启动、状态查询、取消、清理。"""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._active_id: str | None = None
        self._lock = threading.RLock()

    def start(
        self,
        kind: str,
        title: str,
        target: Callable[[Job, Reporter], dict | None],
        payload: dict | None = None,
    ) -> str:
        """
        启动一个后台任务并立刻返回 jobId。

        target 的签名是 (job, reporter)；返回值会存进 result。
        同一时刻只允许一个任务，重复启动抛 JOB_BUSY。
        """

        with self._lock:
            if self._active_id is not None:
                active = self._jobs.get(self._active_id)
                if active is not None and active.status == "running":
                    raise AppError(
                        "JOB_BUSY",
                        "已有任务在运行，请等它结束或先取消",
                        active.title,
                    )
            job = Job(
                id=uuid.uuid4().hex[:12],
                kind=kind,
                title=title,
                payload=dict(payload or {}),
            )
            self._jobs[job.id] = job
            self._active_id = job.id
            self._prune()

        thread = threading.Thread(
            target=self._run,
            args=(job, target),
            name=f"job-{kind}-{job.id}",
            daemon=True,
        )
        thread.start()
        return job.id

    def _run(self, job: Job, target: Callable[[Job, Reporter], dict | None]) -> None:
        """任务线程主体：统一处理成功、取消、可预期错误和未知异常。"""

        reporter = Reporter(job)
        job.started_at = time.time()
        job.log(f"开始：{job.title}", "info")
        try:
            result = target(job, reporter)
            with job.lock:
                job.result = result
                job.status = "done"
            job.log("任务完成", "success")
        except JobCancelled:
            with job.lock:
                job.status = "cancelled"
            job.log("任务已取消，已写入的产物保留", "warn")
        except AppError as error:
            with job.lock:
                job.status = "failed"
                job.error = error.to_dict()
            job.log(f"任务失败：{error.message}", "error")
            if error.detail:
                job.log(error.detail, "error")
        except Exception as error:  # noqa: BLE001 - 任务线程必须兜底
            with job.lock:
                job.status = "failed"
                job.error = {
                    "code": "INTERNAL",
                    "message": "内部错误",
                    "detail": f"{type(error).__name__}: {error}",
                }
            job.log(f"内部错误：{type(error).__name__}: {error}", "error")
        finally:
            job.ended_at = time.time()
            job.done_event.set()
            with self._lock:
                if self._active_id == job.id:
                    self._active_id = None

    def status(self, job_id: str, since: int = 0) -> dict:
        """查询任务状态；jobId 不存在抛 JOB_NOT_FOUND。"""

        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise AppError("JOB_NOT_FOUND", "任务不存在或已被清理", job_id)
        return job.snapshot(since)

    def cancel(self, job_id: str) -> bool:
        """请求取消；任务已是终态时返回 False。"""

        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise AppError("JOB_NOT_FOUND", "任务不存在或已被清理", job_id)
        if job.status != "running":
            return False
        job.cancel_event.set()
        job.log("收到取消请求，正在停在安全位置…", "warn")
        return True

    def active(self) -> dict | None:
        """返回当前运行中任务的摘要；没有则返回 None。"""

        with self._lock:
            job = self._jobs.get(self._active_id) if self._active_id else None
        if job is None or job.status != "running":
            return None
        return {
            "id": job.id,
            "kind": job.kind,
            "title": job.title,
            "progress": dict(job.progress),
            "elapsed": round(time.time() - job.created_at, 1),
        }

    def _prune(self) -> None:
        """清理最旧的已结束任务，避免内存无限增长。"""

        if len(self._jobs) <= const.JOB_MAX_JOBS:
            return
        finished = sorted(
            (job for job in self._jobs.values() if job.status != "running"),
            key=lambda item: item.created_at,
        )
        for job in finished[: len(self._jobs) - const.JOB_MAX_JOBS]:
            self._jobs.pop(job.id, None)
