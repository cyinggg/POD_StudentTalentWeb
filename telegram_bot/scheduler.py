from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pytz
from telegram import Bot
import os

from .data_reader import load_approved_shifts
from .message_builder import build_duty_message

SG_TZ = pytz.timezone("Asia/Singapore")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
TOPIC_ID = int(os.getenv("TOPIC_ID"))

bot = Bot(token=BOT_TOKEN)

def notify_today():
    today = datetime.now(SG_TZ).date()
    shifts = load_approved_shifts(today)
    msg = build_duty_message(today, shifts)

    bot.send_message(
        chat_id=CHAT_ID,
        message_thread_id=TOPIC_ID,
        text=msg,
        parse_mode="Markdown"
    )

def notify_tomorrow():
    tomorrow = datetime.now(SG_TZ).date() + timedelta(days=1)
    shifts = load_approved_shifts(tomorrow)
    msg = build_duty_message(tomorrow, shifts)

    bot.send_message(
        chat_id=CHAT_ID,
        message_thread_id=TOPIC_ID,
        text=msg,
        parse_mode="Markdown"
    )

def start_scheduler():
    scheduler = BackgroundScheduler(timezone=SG_TZ)

    scheduler.add_job(notify_today, "cron", hour=12, minute=0)
    scheduler.add_job(notify_tomorrow, "cron", hour=18, minute=0)

    scheduler.start()
