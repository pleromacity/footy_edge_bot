"""
Thread-safe status tracker for jobs that run in the background (scan, grade).
The web dashboard polls this to show "running..." / "done" without blocking
the page on a long-running API call.
"""

import threading
import time

_lock = threading.Lock()
_state = {
    "scan": {"running": False, "started_at": None, "finished_at": None, "result": None, "error": None},
    "grade": {"running": False, "started_at": None, "finished_at": None, "result": None, "error": None},
}


def start(job_name: str):
    with _lock:
        _state[job_name] = {
            "running": True, "started_at": time.time(),
            "finished_at": None, "result": None, "error": None,
        }


def finish(job_name: str, result=None, error: str = None):
    with _lock:
        _state[job_name]["running"] = False
        _state[job_name]["finished_at"] = time.time()
        _state[job_name]["result"] = result
        _state[job_name]["error"] = error


def get(job_name: str) -> dict:
    with _lock:
        return dict(_state[job_name])


def is_running(job_name: str) -> bool:
    with _lock:
        return _state[job_name]["running"]
