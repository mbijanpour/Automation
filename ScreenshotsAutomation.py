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

# admin chat id , bot tokens , screenshot dir
SCREENSHOT_DIR = SCREENSHOT_DIR
TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = TELEGRAM_CHAT_ID

# setting up DB connections
conn = sqlite3.connect("Telegram_bot.db", check_same_thread=False)
cursor = conn.cursor()

# defining states for handling monitoring process
monitoring = False
monitoring_event = threading.Event()  # the event is use to manage the thread

# the Table user for storing the users
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

# initiating the bot with timeouts and token
req = Request(connect_timeout=1.0, read_timeout=1.0)
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN, request=req)


class ScreenshotHandler(FileSystemEventHandler):
    """
    ScreenshotHandler is a class that inherits from FileSystemEventHandler to monitor
    a specified directory for new screenshot files (PNG, JPG, JPEG). When a new file
    is detected, it processes the file and sends it to a Telegram chat.
    Methods:
        on_created(event):
            Listens for new files created in the monitored directory. If the new file
            is a screenshot (PNG, JPG, JPEG), it sends the file to a Telegram chat.
        send_screenshot(screenshot_path):
            Opens the screenshot file in binary mode and sends it to a Telegram chat
            using a bot.
    """

    def on_created(self, event):
        """
            this method is for listening to the directory activity as the said
            files created.
        """

        if event.is_directory:
            return

        if event.src_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            print(f"Screenshot detected: {event.src_path}")

        time.sleep(0.5)  # ensure that the file creates.

        try:
            asyncio.run(self.send_screenshot(event.src_path))
            print("Screenshot sent to Telegram")
        except Exception as e:
            print(f"Error sending screenshot to Telegram: {e}")

    async def send_screenshot(self, screenshot_path):
        """
            this method is to open the file as 'rb' (the images file should be open as binary)
            and pass it to the bot.
        """

        with open(screenshot_path, 'rb') as file:
            bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=file)


def save_user(user_id, username, first_name, last_name):
    """
    Inserts a new user into the database.
    Args:
        user_id (int): The unique identifier for the user.
        username (str): The username of the user.
        first_name (str): The first name of the user.
        last_name (str): The last name of the user.
    Raises:
        sqlite3.IntegrityError: If there is an integrity constraint violation.
    """

    try:
        cursor.execute("INSERT INTO users(user_id, username, first_name, last_name) VALUES(?, ?, ?, ?)",
                       (user_id, username, first_name, last_name))
        conn.commit()

        print(f"New user {user_id} - {username} inserted")

    except sqlite3.IntegrityError as e:
        print("insertion failed due to:" + e)


def start(update, context):
    """
    Handles the /start command of the bot.
    This function is triggered when the user sends the /start command. It registers the user by saving their details and sends a welcome message.
    Args:
        update (telegram.Update): Incoming update.
        context (telegram.ext.CallbackContext): Context for the callback.
    Returns:
        None
    """

    user = update.message.from_user
    save_user(user.id, user.username, user.first_name, user.last_name)
    update.message.reply_text(
        f"Hello {user.first_name}, you have been registered!")


def stop(update, context):
    """
    Stops the monitoring process of the bot.
    This function is triggered by the stop command of the bot. It sets the 
    monitoring_event to stop the screenshot thread and sets the monitoring 
    flag to False to indicate that monitoring has stopped.
    Args:
        update (telegram.Update): The update object that contains information 
                                  about the incoming update.
        context (telegram.ext.CallbackContext): The context object that contains 
                                                data related to the current state 
                                                of the conversation.
    Returns:
    """

    # the event will be set() in order to stop the thread that is used in def screenshot()
    # also the monitoring will be set to false
    global monitoring_event
    monitoring_event.set()
    global monitoring
    monitoring = False
    update.message.reply_text("Monitoring stopped")


def screenshot(update, context):
    """
    Handles the screenshot monitoring process. This function starts a new thread
    to monitor a specified directory for new screenshots and sends a message to
    the user indicating that monitoring has started.
    Args:
        update (telegram.Update): The update object that contains information about
                                  the incoming update.
        context (telegram.ext.CallbackContext): The context object that contains
                                                information about the current context.
    Globals:
        monitoring (bool): A flag indicating whether monitoring is active.
        monitoring_event (threading.Event): An event object used to control the monitoring loop.
    Side Effects:
        Sends a message to the user indicating that monitoring has started.
        Starts a new thread to monitor the specified directory for new screenshots.
    Raises:
        None
    """
    global monitoring
    global monitoring_event

    # ensures that the pervious thread has stopped
    monitoring = False
    monitoring_event.set()

    monitoring_event = threading.Event()
    monitoring = True

    if update.message:
        update.message.reply_text("Monitoring...")
    # the else is for handling via the admin panel buttons (doesn't have message)
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
                # check if the monitoring is still going and the thread is false (meaning its open)
                time.sleep(0.5)
        except KeyboardInterrupt:
            observer.stop()
        observer.stop()
        observer.join()

    # creating the thread for the screenshot loop
    monitor_thread = threading.Thread(target=monitor)
    monitor_thread.start()


def admin(update, context):
    """
    Handles the admin command for the Telegram bot.

    This function checks if the user issuing the command is the admin by comparing
    the user's ID with the predefined TELEGRAM_CHAT_ID. If the user is the admin,
    it sends a message granting admin activities and displays an admin panel with
    options for taking a screenshot, sending a message to all users, or sending a
    message to a specific user.

    Args:
        update (telegram.Update): Incoming update from Telegram.
        context (telegram.ext.CallbackContext): Context for the callback.

    Returns:
        None
    """

    user = update.message.from_user
    # check if the incoming update is from the admin
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
    """
    Handles callback queries from inline buttons from the admin panel (for now).
    Args:
        update (telegram.Update): Incoming update object that contains the callback query.
        context (telegram.ext.CallbackContext): Context object that contains bot and user data.
    The function processes the callback query data and performs actions based on the query data:
    - If the data is 'screenshot', it calls the screenshot function.
    - If the data is 'send_all', it prompts the user to send a broadcast message to all users.
    - If the data is 'send_user', it prompts the user to send a message to a specific user in the format: user_id:message.
    """

    # contains information about the incoming callback query,
    # including the user credentials that triggered the query.
    query = update.callback_query
    query.answer()


def button(update, context):
    """
    Handles callback queries from inline buttons from the admin panel (for now).
    Args:
        update (telegram.Update): Incoming update object that contains the callback query.
        context (telegram.ext.CallbackContext): Context object that contains bot and user data.
    The function processes the callback query data and performs actions based on the query data:
    - If the data is 'screenshot', it calls the screenshot function.
    - If the data is 'send_all', it prompts the user to send a broadcast message to all users.
    - If the data is 'send_user', it prompts the user to send a message to a specific user in the format: user_id:message.
    """

    # contains information about the incoming callback query,
    # including the user credentials that triggered the query.
    query = update.callback_query
    query.answer()

    # The context object is used to send messages, manage user and chat data, and interact with the bot.
    if query.data == 'screenshot':
        screenshot(update, context)
    elif query.data == 'send_all':
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Please send the message you want to broadcast to all users."
        )
        context.user_data['broadcast'] = True
    elif query.data == 'send_user':
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Please send the user ID and the message you want to send in the format: user_id:message"
        )
        context.user_data['send_user'] = True


def handle_message(update, context):
    """
    Handles incoming messages and performs actions based on user input and context.
    If the user is an admin (determined by TELEGRAM_CHAT_ID), the function can:
    - Broadcast messages, stickers, photos, videos, documents, or animations to all users.
    - Send a direct message to a specific user.
    - Update a user's ID.
    If the user is not an admin, the function forwards the message to the admin.
    Parameters:
    update (telegram.Update): Incoming update from the Telegram bot.
    context (telegram.ext.CallbackContext): Context object passed by the handler.
    Actions based on user input:
    - Text message: Broadcasts or forwards the text message.
    - Sticker: Broadcasts or forwards the sticker.
    - Photo: Broadcasts or forwards the photo.
    - Video: Broadcasts or forwards the video.
    - Document: Broadcasts or forwards the document.
    - Animation: Broadcasts or forwards the animation.
    Exceptions:
    - Handles unauthorized errors when a user has blocked the bot.
    """

    user = update.message.from_user

    # handles the admin panel button actions
    if user.id == int(TELEGRAM_CHAT_ID):
        if context.user_data.get('broadcast'):
            # get all the users.
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()

            if update.message.text:
                message = update.message.text
                for user in users:
                    try:
                        context.bot.send_message(
                            chat_id=user[0], text=message)  # user is a set
                    except telegram.error.Unauthorized:  # unauthorized is for the users who blocked the bot
                        print(f"User {user[0]} has blocked the bot.")

            elif update.message.sticker:
                sticker = update.message.sticker.file_id
                for user in users:
                    try:
                        context.bot.send_sticker(
                            chat_id=user[0], sticker=sticker)
                    except telegram.error.Unauthorized:
                        print(f"User {user[0]} has blocked the bot.")

            elif update.message.photo:
                photo = update.message.photo[-1].file_id
                for user in users:
                    try:
                        context.bot.send_photo(
                            chat_id=user[0], photo=photo)
                    except telegram.error.Unauthorized:
                        print(f"User {user[0]} has blocked the bot.")

            elif update.message.video:
                video = update.message.video.file_id
                for user in users:
                    try:
                        context.bot.send_video(
                            chat_id=user[0], video=video)
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

        elif context.user_data.get('send_user'):
            try:
                id, message = update.message.text.split(':', 1)
                context.bot.send_message(chat_id=id, text=message)
                update.message.reply_text("Message sent to user.")
            except ValueError:
                update.message.reply_text(
                    "Invalid format. Please use the format: user_id:message")
            except telegram.error.Unauthorized:
                print(f"User {id} has blocked the bot.")
            context.user_data['send_user'] = False
    else:  # if the user is not admin
        print(f"A message from {user.username} - {user.id}")

        if update.message.text:
            message = update.message.text
            context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

        elif update.message.video:
            video = update.message.video.file_id
            context.bot.send_video(chat_id=TELEGRAM_CHAT_ID, video=video)

        elif update.message.photo:
            photo = update.message.photo[-1].file_id
            context.bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=photo)

        elif update.message.document:
            document = update.message.document.file_id
            context.bot.send_document(
                chat_id=TELEGRAM_CHAT_ID, document=document)

        elif update.message.sticker:
            photo = update.message.photo[-1].file_id
            context.bot.send_sticker(chat_id=TELEGRAM_CHAT_ID, sticker=sticker)

        elif update.message.animation:
            animation = update.message.animation.file_id
            context.bot.send_animation(
                chat_id=TELEGRAM_CHAT_ID, animation=animation)


# setting up the updater for the bot
updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# setting up the commands and the Query handlers for the buttons
dispatcher.add_handler(CallbackQueryHandler(button))
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("screenshot", screenshot))
dispatcher.add_handler(CommandHandler("admin", admin))
dispatcher.add_handler(CommandHandler("stop", stop))

# This line adds a handler for text messages that are not commands.
dispatcher.add_handler(MessageHandler(
    Filters.text & ~Filters.command, handle_message))

# the handlers for other messages type like photos, videos, docs and ...
dispatcher.add_handler(MessageHandler(Filters.photo, handle_message))
dispatcher.add_handler(MessageHandler(Filters.video, handle_message))
dispatcher.add_handler(MessageHandler(Filters.document, handle_message))
dispatcher.add_handler(MessageHandler(Filters.sticker, handle_message))
dispatcher.add_handler(MessageHandler(Filters.animation, handle_message))

# bot starting
updater.start_polling()
updater.idle()
