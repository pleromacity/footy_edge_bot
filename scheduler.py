"""
Runs scan and grade automatically on a schedule, so you don't have to
remember to click buttons every day. Controlled from the web dashboard's
Settings page (auto_scan_enabled, scan_time, grade_time).

This only runs while webapp.py is running -- it's an in-process scheduler,
not a separate Windows service. If you close the web app, scheduled jobs
stop firing until you start it again.
"""

from apscheduler.schedulers.background import BackgroundScheduler

import job_state
import settings as settings_module
from logging_setup import setup_logging

logger = setup_logging()
_scheduler = None


def _run_scan_job():
    if job_state.is_running("scan"):
        logger.info("Scheduled scan skipped -- a scan is already running.")
        return
    import main as scan_module  # imported here to avoid circular imports at module load
    job_state.start("scan")
    try:
        bets = scan_module.run()
        job_state.finish("scan", result={"count": len(bets)})
        logger.info(f"Scheduled scan complete: {len(bets)} value bet(s) found.")
    except Exception as e:
        logger.exception("Scheduled scan failed")
        job_state.finish("scan", error=str(e))


def _run_grade_job():
    if job_state.is_running("grade"):
        logger.info("Scheduled grading skipped -- grading is already running.")
        return
    import grade as grade_module
    job_state.start("grade")
    try:
        result = grade_module.run()
        job_state.finish("grade", result=result)
        logger.info(f"Scheduled grading complete: {result}")
    except Exception as e:
        logger.exception("Scheduled grading failed")
        job_state.finish("grade", error=str(e))


def init_scheduler():
    """Call once, at web app startup. Safe to call multiple times -- only
    the first call actually starts anything."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    s = settings_module.load_settings()
    if not s.get("auto_scan_enabled"):
        logger.info("Auto-scan scheduling is disabled (enable it in Settings).")
        return None

    scan_h, scan_m = map(int, s.get("scan_time", "08:00").split(":"))
    grade_h, grade_m = map(int, s.get("grade_time", "23:00").split(":"))

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(_run_scan_job, "cron", hour=scan_h, minute=scan_m,
                       id="daily_scan", replace_existing=True)
    scheduler.add_job(_run_grade_job, "cron", hour=grade_h, minute=grade_m,
                       id="daily_grade", replace_existing=True)
    scheduler.start()
    _scheduler = scheduler
    logger.info(f"Scheduler started -- scan daily at {s.get('scan_time')}, "
                f"grade daily at {s.get('grade_time')}.")
    return scheduler


def reload_scheduler():
    """Call after settings change, so a schedule toggle/time change takes
    effect without restarting the whole web app."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
    return init_scheduler()
