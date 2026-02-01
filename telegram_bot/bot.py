# bot.py
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
import os

from .handlers import main_menu, handle_menu
from .scheduler import start_scheduler

BOT_TOKEN = os.getenv("BOT_TOKEN")

def start_bot():
    print("Telegram bot initializing")

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler(
        "start",
        lambda u, c: c.bot.send_message(
            chat_id=u.effective_chat.id,
            text="👋 ProjectHub Duty Bot",
            reply_markup=main_menu()
        )
    ))

    dp.add_handler(CallbackQueryHandler(
        lambda u, c: handle_menu(u.callback_query, c.bot)
    ))

    start_scheduler()

    print("Telegram bot polling started")
    updater.start_polling()
    updater.idle()   # ← IMPORTANT for clean shutdown
