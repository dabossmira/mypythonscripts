import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def send_email(subject, body, receiver_email):
    sender_email = os.getenv("EMAIL_ADDRESS")  # Updated variable name
    sender_password = os.getenv("EMAIL_PASSWORD")  # Updated variable name

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

# Example usage
if __name__ == "__main__":
    send_email("Test Subject", "Test Body", "mirasplendid2017@gmail.com")
