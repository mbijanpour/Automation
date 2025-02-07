# Telegram Screenshot Monitoring Bot

This project is a Telegram bot that monitors a specified directory for new screenshot files and sends them to a Telegram chat. It also includes features for broadcasting messages to all users and sending messages to specific users.

## Features

- Monitors a specified directory for new screenshot files (PNG, JPG, JPEG) and sends them to a Telegram chat.
- Allows the admin to broadcast messages, stickers, photos, videos, documents, or animations to all users.
- Allows the admin to send a direct message to a specific user.
- Registers new users and stores their information in a SQLite database.

## Requirements

- Python 3.6+
- `python-telegram-bot` library
- `watchdog` library
- `sqlite3` library

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/telegram-screenshot-monitoring-bot.git
    cd telegram-screenshot-monitoring-bot
    ```

2. Install the required libraries:

    ```bash
    pip install python-telegram-bot watchdog
    ```

3. Create a [keys.py](http://_vscodecontentref_/0) file with the following content:

    ```python
    SCREENSHOT_DIR = "path/to/your/screenshot/directory"
    TELEGRAM_BOT_TOKEN = "your-telegram-bot-token"
    TELEGRAM_CHAT_ID = "your-telegram-chat-id"
    ```

4. Ensure that the [Telegram_bot.db](http://_vscodecontentref_/1) SQLite database file exists and has the following schema:

    ```sql
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT,
        first_name TEXT,
        last_name TEXT
    );
    ```

## Usage

1. Start the bot:

    ```bash
    python ScreenshotsAutomation.py
    ```

2. Use the following commands in your Telegram chat:

    - `/start`: Registers the user and sends a welcome message.
    - `/screenshot`: Starts monitoring the specified directory for new screenshots.
    - `/stop`: Stops the monitoring process.
    - `/admin`: Opens the admin panel with options for taking a screenshot, sending a message to all users, or sending a message to a specific user.

## Code Overview

### Imports and Initial Setup

The necessary libraries are imported, and global variables and database connections are set up.

### ScreenshotHandler Class

This class inherits from [FileSystemEventHandler](http://_vscodecontentref_/2) and monitors the specified directory for new screenshot files. When a new file is detected, it sends the file to a Telegram chat.

### User Management Functions

Functions for saving user information in the database.

### Command Handlers

Functions for handling the `/start`, `/stop`, `/screenshot`, and `/admin` commands.

### Callback Query Handler

Function for handling callback queries from inline buttons in the admin panel.

### Message Handler

Function for handling incoming messages and performing actions based on user input and context.

### Setting Up the Bot

The bot is set up with the necessary handlers and starts polling for updates.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## Acknowledgements

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [watchdog](https://github.com/gorakhargosh/watchdog)
