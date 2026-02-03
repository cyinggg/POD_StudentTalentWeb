# -------------------- LOAD .ENV FIRST --------------------
from dotenv import load_dotenv
load_dotenv()  # now all environment variables are available

# -------------------- STANDARD IMPORTS --------------------
import threading
import os

from webpage import app
from telegram_bot.runner import run_bot

# -------------------- FLASK --------------------
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ==========================
# RUN
# ==========================
if __name__ == "__main__":
    print("Starting Flask web and Telegram bot")

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Start Telegram bot (blocks forever)
    run_bot()