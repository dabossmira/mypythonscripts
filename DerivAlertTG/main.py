import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.ext import ConversationHandler
import asyncio
import websockets
import json

# File where user settings will be saved
USER_DATA_FILE = "user_data.json"

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define constants for conversation states
EMAIL, INSTRUMENT, ALERT_PRICE, CUSTOM_MESSAGE = range(4)

# Load user data from file
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save user data to file
def save_user_data(user_data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(user_data, f, indent=4)

# Load the existing user data when the bot starts
all_user_data = load_user_data()

# Function to send an email
def send_email(subject, body, receiver_email):
    sender_email = os.getenv("EMAIL_ADDRESS")
    sender_password = os.getenv("EMAIL_PASSWORD")

    # Create the email content
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to the Gmail SMTP server on port 465
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
            logger.info("Email sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

# Function to monitor price and send alerts using WebSocket
async def monitor_price(instrument, alert_price, email, custom_message, chat_id, context):
    deriv_api_url = os.getenv("DERIV_API_URL")  # Get the URL from the .env file

    async with websockets.connect(deriv_api_url) as websocket:
        # Subscribe to price updates for the selected instrument
        subscribe_message = {
            "ticks": instrument
        }
        await websocket.send(json.dumps(subscribe_message))

        logger.info(f"Monitoring {instrument} for price {alert_price}")

        while True:
            response = await websocket.recv()
            data = json.loads(response)

            if "tick" in data:
                current_price = data["tick"]["quote"]
                logger.info(f"Current price of {instrument}: {current_price}")

                if current_price >= alert_price:  # Check if the price level is reached
                    # Send email and notify via Telegram
                    send_email("Price Alert Triggered", f"{custom_message} - The price has reached your alert level: {current_price}.", email)
                    await context.bot.send_message(chat_id=chat_id, text=f"Price Alert: {custom_message} - The price has reached {current_price}. An email alert has been sent.")
                    break  # Exit the loop after sending the alert

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    context.user_data["chat_id"] = chat_id  # Store chat_id automatically

    # Check if user data exists and load settings
    if chat_id in all_user_data:
        user_settings = all_user_data[chat_id]
        context.user_data.update(user_settings)  # Load saved data into the current session
        await context.bot.send_message(chat_id=chat_id, text=f"Welcome back! Your saved settings are:\n"
                                                              f"Email: {user_settings.get('email')}\n"
                                                              f"Instrument: {user_settings.get('instrument')}\n"
                                                              f"Alert Price: {user_settings.get('alert_price')}\n"
                                                              f"Custom Message: {user_settings.get('custom_message')}")
    else:
        await context.bot.send_message(chat_id=chat_id, text="Welcome! Use /setemail to set your email address.")

# Command to set email address
async def set_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please enter your email address:")
    return EMAIL

# Handle user input for email
async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text
    chat_id = str(update.message.chat_id)
    context.user_data["email"] = email  # Store email in user_data

    # Save email to persistent storage
    all_user_data[chat_id] = context.user_data
    save_user_data(all_user_data)

    await update.message.reply_text(f"Email set to: {email}. You can now set an alert using /setalert.")
    return ConversationHandler.END

# Command to set an alert
async def set_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instrument_hint = ("Please enter the instrument name from the following list:\n\n"
                       "VOLATILITY 10 INDEX = 'R_10'\n"
                       "VOLATILITY 25 INDEX = 'R_25'\n"
                       "VOLATILITY 50 INDEX = 'R_50'\n"
                       "VOLATILITY 75 INDEX = 'R_75'\n"
                       "VOLATILITY 100 INDEX = 'R_100'\n"
                       "VOLATILITY 10(1S) INDEX = '1HZ10V'\n"
                       "VOLATILITY 25(1S) INDEX = '1HZ25V'\n"
                       "VOLATILITY 50(1S) INDEX = '1HZ50V'\n"
                       "VOLATILITY 75(1S) INDEX = '1HZ75V'\n"
                       "VOLATILITY 100(1S) INDEX = '1HZ100V'\n"
                       "VOLATILITY 150(1S) INDEX = '1HZ150V'\n"
                       "VOLATILITY 250(1S) INDEX = '1HZ250V'\n"
                       "BOOM 300 INDEX = 'BOOM300N'\n"
                       "BOOM 500 INDEX = 'BOOM500N'\n"
                       "BOOM 1000 INDEX = 'BOOM1000'\n"
                       "CRASH 300 INDEX = 'CRASH300N'\n"
                       "CRASH 500 INDEX = 'CRASH500'\n"
                       "CRASH 1000 INDEX = 'CRASH1000'\n"
                       "JUMP 10 INDEX = 'JD10'\n"
                       "JUMP 25 INDEX = 'JD25'\n"
                       "JUMP 50 INDEX = 'JD50'\n"
                       "JUMP 75 INDEX = 'JD75'\n"
                       "JUMP 100 INDEX = 'JD100'\n")

    await update.message.reply_text(instrument_hint)
    return INSTRUMENT

# Handle user input for instrument
async def handle_instrument(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instrument = update.message.text
    chat_id = str(update.message.chat_id)
    context.user_data["instrument"] = instrument  # Store instrument in user_data

    # Save instrument to persistent storage
    all_user_data[chat_id] = context.user_data
    save_user_data(all_user_data)

    await update.message.reply_text("Please enter your custom message:")
    return CUSTOM_MESSAGE

# Handle user input for custom message
async def handle_custom_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    custom_message = update.message.text
    chat_id = str(update.message.chat_id)
    context.user_data["custom_message"] = custom_message  # Store custom message in user_data

    # Save custom message to persistent storage
    all_user_data[chat_id] = context.user_data
    save_user_data(all_user_data)

    await update.message.reply_text("Please enter the price at which you want to set the alert:")
    return ALERT_PRICE

# Handle user input for alert price
async def handle_alert_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        chat_id = str(update.message.chat_id)
        context.user_data["alert_price"] = price  # Store alert price in user_data

        # Save alert price to persistent storage
        all_user_data[chat_id] = context.user_data
        save_user_data(all_user_data)

        # Notify user of alert setup
        await update.message.reply_text(f"Alert set for {context.user_data['instrument']} at price: {price}.\n"
                                         f"You will be notified via email and Telegram with your message: {context.user_data['custom_message']}.")

        # Start monitoring price in the background
        asyncio.create_task(monitor_price(context.user_data['instrument'], price, context.user_data["email"], context.user_data["custom_message"], context.user_data["chat_id"], context))

    except ValueError:
        await update.message.reply_text("Invalid price. Please enter a numeric value.")
        return ALERT_PRICE

    return ConversationHandler.END

# Command to view current settings
async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    if chat_id in all_user_data:
        user_settings = all_user_data[chat_id]
        settings_message = (f"Your current settings are:\n"
                            f"Email: {user_settings.get('email')}\n"
                            f"Instrument: {user_settings.get('instrument')}\n"
                            f"Alert Price: {user_settings.get('alert_price')}\n"
                            f"Custom Message: {user_settings.get('custom_message')}")
        await context.bot.send_message(chat_id=chat_id, text=settings_message)
    else:
        await context.bot.send_message(chat_id=chat_id, text="No settings found. Please set your email and alert.")

# Command to modify email
async def modify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please enter your new email address:")
    return EMAIL

# Command to cancel conversation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

def main():
    # Create the Application and pass it your bot's token
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    # Set up conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("setemail", set_email),
                      CommandHandler("setalert", set_alert),
                      CommandHandler("view", view),
                      CommandHandler("modify", modify)],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)],
            INSTRUMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instrument)],
            CUSTOM_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_message)],
            ALERT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_alert_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
