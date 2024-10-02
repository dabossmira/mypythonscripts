import os
import websocket
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import telebot
from dotenv import load_dotenv
import logging

# Load environment variables from the .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
TO_EMAIL = os.getenv('TO_EMAIL')
DERIV_API_URL = os.getenv('DERIV_API_URL')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Initialize the Telegram bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Email and Telegram Configuration
alert_prices = {}

def send_email(subject, message):
    """Function to send email using SSL."""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = TO_EMAIL
    msg['Subject'] = subject

    msg.attach(MIMEText(message, 'plain'))
    try:
        # Connect to the SMTP server using SSL
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
            print(f"Email sent to {TO_EMAIL}")
    except Exception as e:
        print(f"Failed to send email. Error: {e}")

def send_telegram_message(message):
    """Function to send a message to Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        print("Message sent to Telegram.")
    except Exception as e:
        print(f"Error sending message to Telegram: {e}")

# Function to handle incoming WebSocket messages
def on_message(ws, message):
    data = json.loads(message)
    if 'tick' in data:
        symbol = data['tick']['symbol']
        price = data['tick']['quote']
        timestamp = data['tick']['epoch']
        print(f"Instrument: {symbol}, Price: {price}, Timestamp: {timestamp}")

        # Define a small tolerance for price comparison
        tolerance = 0.1  # Adjust this value as needed for your use case

        # Check if the price is within the tolerance range of the alert threshold
        if symbol in alert_prices:
            target_price = alert_prices[symbol]['target_price']
            custom_message = alert_prices[symbol]['custom_message']
            if abs(price - target_price) <= tolerance:  # Use tolerance for comparison
                alert_message = f"ALERT: {symbol} has reached the desired price of {target_price}! The current price is: {price}\n{custom_message}"
                print(f"*** {alert_message} ***")

                # Send an email alert
                send_email(subject=f"Price Alert for {symbol}", message=alert_message)

                # Send a Telegram alert
                send_telegram_message(alert_message)

                # Remove the instrument from the alert list
                del alert_prices[symbol]

                # Check if all alerts are done, then close WebSocket
                if not alert_prices:
                    print("All price alerts have been triggered. Closing WebSocket connection.")
                    ws.close()

# WebSocket handlers
def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")

def on_open(ws):
    print("WebSocket connection opened")
    # Subscribe to tick updates for each instrument
    for instrument in alert_prices.keys():
        subscribe_message = json.dumps({"ticks": instrument})
        ws.send(subscribe_message)

# Telegram Bot Commands
@bot.message_handler(commands=['start'])
def start(message):
    """Send a welcome message when the /start command is issued."""
    logger.info("Received /start command.")
    bot.reply_to(message, 'Hello! Welcome to the Deriv Price Alert Bot.')

@bot.message_handler(commands=['setalert'])
def set_alert(message):
    """Set an alert for an instrument."""
    try:
        args = message.text.split()[1:]  # Split message text by spaces and remove command
        instrument = args[0]
        target_price = float(args[1])
        custom_message = ' '.join(args[2:]) if len(args) > 2 else 'Price Alert Set!'
        alert_prices[instrument] = {'target_price': target_price, 'custom_message': custom_message}
        logger.info(f'Alert set for {instrument} at price {target_price}.')
        bot.reply_to(message, f'Alert set for {instrument} at price {target_price}.')
    except (IndexError, ValueError):
        logger.warning('Invalid input for /setalert command.')
        bot.reply_to(message, 'Usage: /setalert <instrument> <target_price> <optional_custom_message>')

# Run the Telegram bot
def run_bot():
    """Starts the Telegram bot."""
    bot.polling(none_stop=True)

def run_websocket():
    """Runs the WebSocket connection."""
    ws = websocket.WebSocketApp(DERIV_API_URL,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)

    ws.run_forever()

# Main function to run both WebSocket and Telegram Bot concurrently
if __name__ == "__main__":
    import threading

    # Start the Telegram bot in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    # Run the WebSocket connection in the main thread
    run_websocket()
