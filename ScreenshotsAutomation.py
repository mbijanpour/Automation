import os
import time
import telegram
import asyncio
import sqlite3
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
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
        keyboard = [
            [InlineKeyboardButton(text="Screenshot",
                                  callback_data='screenshot')],
            [InlineKeyboardButton(text="Send to all",
                                  callback_data='send_all')],
            [InlineKeyboardButton(text="Send to user",
                                  callback_data='send_user')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Admin panel', reply_markup=reply_markup)
    else:
        return


def button(update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'screenshot':
        screenshot(update, context)
    elif query.data == 'send_all':
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Please send the message you want to broadcast to all users."
        )
        context.user_data['broadcast'] = True


def handle_message(update, context):
    if context.user_data.get('broadcast'):
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        if update.message.text:
            message = update.message.text
            for user in users:
                try:
                    context.bot.send_message(chat_id=user[0], text=message)
                except telegram.error.Unauthorized:
                    print(f"User {user[0]} has blocked the bot.")
        elif update.message.sticker:
            sticker = update.message.sticker.file_id
            for user in users:
                try:
                    context.bot.send_sticker(chat_id=user[0], sticker=sticker)
                except telegram.error.Unauthorized:
                    print(f"User {user[0]} has blocked the bot.")
        elif update.message.photo:
            photo = update.message.photo[-1].file_id
            for user in users:
                try:
                    context.bot.send_photo(chat_id=user[0], photo=photo)
                except telegram.error.Unauthorized:
                    print(f"User {user[0]} has blocked the bot.")
        elif update.message.video:
            video = update.message.video.file_id
            for user in users:
                try:
                    context.bot.send_video(chat_id=user[0], video=video)
                except telegram.error.Unauthorized:
                    print(f"User {user[0]} has blocked the bot.")
        elif update.message.document:
            document = update.message.document.file_id
            for user in users:
                try:
                    context.bot.send_document(
                        chat_id=user[0], document=document)
                except telegram.error.Unauthorized:
                    print(f"User {user[0]} has blocked the bot.")
        elif update.message.animation:
            animation = update.message.animation.file_id
            for user in users:
                try:
                    context.bot.send_animation(
                        chat_id=user[0], animation=animation)
                except telegram.error.Unauthorized:
                    print(f"User {user[0]} has blocked the bot.")

        context.user_data['broadcast'] = False
    elif context.user_data.get('update_user_id'):
        new_user_id = update.message.text
        update_user_id(new_user_id)
        context.user_data['update_user_id'] = False


updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

dispatcher.add_handler(CallbackQueryHandler(button))
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("screenshot", screenshot))
dispatcher.add_handler(CommandHandler("admin", admin))
dispatcher.add_handler(CommandHandler("stop", stop))
dispatcher.add_handler(MessageHandler(
    Filters.text & ~Filters.command, handle_message))
dispatcher.add_handler(MessageHandler(Filters.photo, handle_message))
dispatcher.add_handler(MessageHandler(Filters.video, handle_message))
dispatcher.add_handler(MessageHandler(Filters.document, handle_message))
dispatcher.add_handler(MessageHandler(Filters.sticker, handle_message))
dispatcher.add_handler(MessageHandler(Filters.animation, handle_message))

updater.start_polling()
updater.idle()
