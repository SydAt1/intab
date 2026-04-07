import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.core import config

def send_reset_email(to_email: str, token: str):
    """
    Sends a password reset email to the specified user.
    """
    # Create the reset link
    reset_link = f"http://localhost:8000/reset-password?token={token}"
    
    # Create the email message
    subject = "Password Reset Request - Audio Tablature Studio"
    body = f"""
    <html>
    <body>
        <h2>Password Reset Request</h2>
        <p>Hello,</p>
        <p>You requested to reset your password for Audio Tablature Studio. Please click the link below to set a new password:</p>
        <p><a href="{reset_link}">{reset_link}</a></p>
        <p>This link will expire in 1 hour.</p>
        <p>If you did not request this, please ignore this email.</p>
        <br>
        <p>Best regards,<br>The InTab Team</p>
    </body>
    </html>
    """
    
    msg = MIMEMultipart()
    msg['From'] = config.FROM_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        # Connect to the SMTP server
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
