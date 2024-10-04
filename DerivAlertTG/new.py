import asyncio
import nest_asyncio
import websockets
import json
import smtplib
from email.mime.text import MIMEText
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Allow nested event loops
nest_asyncio.apply()

# Inline environment variables
TELEGRAM_BOT_TOKEN = '7374323759:AAEuwSKA6P3-X1xzJWfYAZvHZHV_NaLgQww'
EMAIL_ADDRESS = 'mirasplendid2017@gmail.com'
EMAIL_PASSWORD = 'mqgeenoihhdrwghr'
DERIV_API_URL = 'wss://ws.binaryws.com/websockets/v3?app_id=1089'

# Global variable for tracking price alerts
price_alerts = {}

# List of available instruments
instruments = [
    'VOLATILITY 10 INDEX', 
    'VOLATILITY 25 INDEX', 
    'VOLATILITY 50 INDEX', 
    'VOLATILITY 75 INDEX', 
    'VOLATILITY 100 INDEX', 
    'BOOM 1000 INDEX', 
    'CRASH 1000 INDEX', 
    'JUMP 50 INDEX'
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Welcome to the Deriv Alert Bot! Use /set_alert to create a price alert or /available_instruments to see the list of available instruments.')

async def available_instruments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    instruments_list = "\n".join(instruments)
    await update.message.reply_text(f'Available instruments:\n{instruments_list}')

async def set_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        instrument = context.args[0]  # First argument is the instrument
        target_price = float(context.args[1])  # Second argument is the target price
        custom_message = " ".join(context.args[2:])  # Remaining arguments are the custom message
        
        if instrument not in instruments:
            await update.message.reply_text(f'Invalid instrument. Use /available_instruments to see valid options.')
            return

        price_alerts[instrument] = (target_price, custom_message)
        
        await update.message.reply_text(f'Alert set for {instrument} at {target_price} with message: "{custom_message}"')
    except (IndexError, ValueError):
        await update.message.reply_text('Usage: /set_alert <instrument> <target_price> <message>')

async def notify_user(message: str):
    # Send email notification
    msg = MIMEText(message)
    msg['Subject'] = 'Price Alert Notification'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS  # Send to the same email or change as needed

    with smtplib.SMTP('smtp.gmail.com', 587) as server:  # Gmail SMTP server
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)  # Use your email credentials
        server.send_message(msg)

async def price_data_listener():
    async with websockets.connect(DERIV_API_URL) as websocket:
        while True:
            data = await websocket.recv()
            price_info = json.loads(data)
            # Assume price_info has 'instrument' and 'price' keys

            for instrument, (target_price, custom_message) in price_alerts.items():
                current_price = price_info['price']

                if current_price >= target_price:  # Trigger alert
                    alert_message = f'Price Alert! {instrument} has reached {current_price}. Message: "{custom_message}"'
                    await notify_user(alert_message)  # Send email notification
                    await notify_telegram(alert_message)  # Send Telegram notification
                    del price_alerts[instrument]  # Remove the alert after notification

async def notify_telegram(message: str):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    await asyncio.create_task(requests.post(telegram_url, data={'chat_id': 'YOUR_CHAT_ID', 'text': message}))

async def main() -> None:
    # Initialize the Telegram bot application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("available_instruments", available_instruments))
    application.add_handler(CommandHandler("set_alert", set_alert))

    # Start the price data listener in the background
    asyncio.create_task(price_data_listener())

    try:
        await application.run_polling()
    except Exception as e:
        raise e

if __name__ == '__main__':
    asyncio.run(main())
