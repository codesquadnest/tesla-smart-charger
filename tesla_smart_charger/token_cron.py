"""
Python script to run the token refresh cron job.
"""

import schedule
import time


def refresh_tesla_token():
    print("Running my cron job!")


def start_cron_job(stop_event):
    # Run the job every minute
    schedule.every(1).minutes.do(refresh_tesla_token)

    while not stop_event.is_set():
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    start_cron_job()
