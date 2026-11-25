from apscheduler.schedulers.blocking import BlockingScheduler

from src.run_pipeline import main
from src.utils.observability import log_error, log_info


def scheduled_job():
    log_info("Scheduled pipeline run started")
    try:
        main()
        log_info("Scheduled pipeline run completed successfully")
    except Exception as e:
        log_error(f"Scheduled pipeline run failed: {str(e)}")


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_job, "cron", day_of_week="sun", hour=2, minute=0)
    log_info("Scheduler started, job will run every Sunday at 2:00 AM")
    scheduler.start()
