"""Deprecated filename — prefer `src/run_scheduler.py`."""

from src.run_scheduler import scheduled_job

if __name__ == "__main__":
    from apscheduler.schedulers.blocking import BlockingScheduler

    from src.utils.observability import log_info

    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_job, "cron", day_of_week="sun", hour=2, minute=0)
    log_info(
        "Scheduler started via deprecated run_schedular.py; prefer src/run_scheduler.py"
    )
    scheduler.start()
