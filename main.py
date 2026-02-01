# main.py
import threading

from webpage import app
from telegram_bot.runner import run_bot


def run_flask():
    # Flask web server for Replit / UptimeRobot
    app.run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    print("🚀 Starting Flask web + Telegram bot")

    # Start Flask in background
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Start Telegram bot (blocks forever)
    run_bot()
