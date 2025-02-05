import os
import time
import telegram
import asyncio
import sqlite3
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.utils.request import Request
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

from keys import *

SCREENSHOT_DIR = SCREENSHOT_DIR
TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = TELEGRAM_CHAT_ID


conn = sqlite3.connect("Telegram_bot.db", check_same_thread=False)
cursor = conn.cursor()

monitoring = False
monitoring_event = threading.Event()

# cursor.execute("""
#     CREATE TABLE IF NOT EXISTS users (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id INTEGER UNIQUE,
#         username TEXT,
#         first_name TEXT,
#         last_name TEXT
#     )
# """)
# conn.commit()

req = Request(connect_timeout=1.0, read_timeout=1.0)
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN, request=req)


class ScreenshotHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        if event.src_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            print(f"Screenshot detected: {event.src_path}")

        time.sleep(0.5)

        try:
            asyncio.run(self.send_screenshot(event.src_path))
            print("Screenshot sent to Telegram")
        except Exception as e:
            print(f"Error sending screenshot to Telegram: {e}")

    async def send_screenshot(self, screenshot_path):
        with open(screenshot_path, 'rb') as file:
            bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=file)


def save_user(user_id, username, first_name, last_name):
    try:
        cursor.execute("INSERT INTO users(user_id, username, first_name, last_name) VALUES(?, ?, ?, ?)",
                       (user_id, username, first_name, last_name))
        conn.commit()

        print("inserted")

    except sqlite3.IntegrityError as e:
        print(e)


def start(update, context):
    user = update.message.from_user
    save_user(user.id, user.username, user.first_name, user.last_name)
    update.message.reply_text(
        f"Hello {user.first_name}, you have been registered!")


def stop(update, context):
    global monitoring_event
    monitoring_event.set()
    global monitoring
    monitoring = False
    update.message.reply_text("Monitoring stopped")


def screenshot(update, context):
    global monitoring
    global monitoring_event

    monitoring = False
    monitoring_event.set()

    monitoring_event = threading.Event()
    monitoring = True

    if update.message:
        update.message.reply_text("Monitoring...")
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Monitoring...")

    def monitor():
        event_handler = ScreenshotHandler()
        observer = Observer()
        observer.schedule(event_handler, path=SCREENSHOT_DIR, recursive=False)
        observer.start()
        print(f"Watching for screenshots in {SCREENSHOT_DIR}")

        try:
            while monitoring and not monitoring_event.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            observer.stop()
        observer.stop()
        observer.join()

    monitor_thread = threading.Thread(target=monitor)
    monitor_thread.start()


def admin(update, context):
    user = update.message.from_user
    if user.id == int(TELEGRAM_CHAT_ID):
        update.message.reply_text("Admin activities granted")
        keyboard = [[InlineKeyboardButton(
            text="Screenshot", callback_data='screenshot')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Admin panel', reply_markup=reply_markup)
    else:
        return


def button(update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'screenshot':
        screenshot(update, context)


updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

dispatcher.add_handler(CallbackQueryHandler(button))

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("screenshot", screenshot))
dispatcher.add_handler(CommandHandler("admin", admin))
dispatcher.add_handler(CommandHandler("stop", stop))

updater.start_polling()
updater.idle()
