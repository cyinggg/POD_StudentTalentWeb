from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .data_reader import load_approved_shifts
from .message_builder import build_duty_message

SG_TZ = ZoneInfo("Asia/Singapore")

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📅 Today", callback_data="today")],
        [InlineKeyboardButton("📆 Tomorrow", callback_data="tomorrow")],
        [InlineKeyboardButton("🔍 Search by Date", callback_data="search_date")],
        [InlineKeyboardButton("👤 Search by Name", callback_data="search_name")]
    ]
    return InlineKeyboardMarkup(keyboard)

def handle_menu(query, bot):
    today = datetime.now(SG_TZ).date()

    if query.data == "today":
        shifts = load_approved_shifts(today)
        msg = build_duty_message(today, shifts)
        bot.send_message(chat_id=query.message.chat_id, text=msg)

    elif query.data == "tomorrow":
        tmr = today + timedelta(days=1)
        shifts = load_approved_shifts(tmr)
        msg = build_duty_message(tmr, shifts)
        bot.send_message(chat_id=query.message.chat_id, text=msg)
