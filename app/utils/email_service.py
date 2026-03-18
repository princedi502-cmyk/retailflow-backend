import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    def send_password_reset_email(self, to_email: str, reset_token: str) -> bool:
        """Send password reset email to user"""
        try:
            # Create reset link
            reset_link = f"{self.frontend_url}/reset-password?token={reset_token}"
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = "Reset Your Password - Retail Flow"
            
            # Email body
            body = f"""
            <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Hello,</p>
                <p>We received a request to reset your password for your Retail Flow account.</p>
                <p>Click the link below to reset your password:</p>
                <p><a href="{reset_link}">Reset Password</a></p>
                <p>Or copy and paste this link in your browser:</p>
                <p>{reset_link}</p>
                <p><strong>Note:</strong> This link will expire in 1 hour for security reasons.</p>
                <p>If you didn't request this password reset, please ignore this email.</p>
                <br>
                <p>Best regards,<br>
                The Retail Flow Team</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Failed to send password reset email: {e}")
            return False
    
    def send_password_reset_confirmation(self, to_email: str) -> bool:
        """Send password reset confirmation email"""
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = "Password Reset Successful - Retail Flow"
            
            # Email body
            body = f"""
            <html>
            <body>
                <h2>Password Reset Successful</h2>
                <p>Hello,</p>
                <p>Your password for your Retail Flow account has been successfully reset.</p>
                <p>If you didn't make this change, please contact our support team immediately.</p>
                <p>You can now log in with your new password.</p>
                <br>
                <p>Best regards,<br>
                The Retail Flow Team</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Failed to send password reset confirmation email: {e}")
            return False
    
    def send_email_verification(self, to_email: str, verification_token: str) -> bool:
        """Send email verification email to user"""
        try:
            # Create verification link
            verification_link = f"{self.frontend_url}/verify-email?token={verification_token}"
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = "Verify Your Email - Retail Flow"
            
            # Email body
            body = f"""
            <html>
            <body>
                <h2>Welcome to Retail Flow!</h2>
                <p>Hello,</p>
                <p>Thank you for registering with Retail Flow. To complete your registration, please verify your email address.</p>
                <p>Click the link below to verify your email:</p>
                <p><a href="{verification_link}">Verify Email Address</a></p>
                <p>Or copy and paste this link in your browser:</p>
                <p>{verification_link}</p>
                <p><strong>Note:</strong> This link will expire in 24 hours for security reasons.</p>
                <p>If you didn't create an account with us, please ignore this email.</p>
                <br>
                <p>Best regards,<br>
                The Retail Flow Team</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Failed to send email verification: {e}")
            return False

# Global email service instance
email_service = EmailService()
