from emails import Message
from jinja2 import Environment, FileSystemLoader
from ..config import settings
from ..models.email_log import EmailLog
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import os
import base64

logger = logging.getLogger(__name__)

def format_date(value):
    """Convert ISO date string to a more readable format"""
    if not value:
        return ""
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        else:
            dt = value
        return dt.strftime("%B %d, %Y")
    except Exception as e:
        logger.error(f"Error formatting date: {str(e)}")
        return value

class EmailService:
    def __init__(self, db: Session):
        self.db = db
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
        # Temporarily disabled logo
        # self.logo_path = os.path.join(assets_dir, 'apple-touch-icon', 'kaupskip-logo-180x180.png')
        self.logo_path = None
        
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True
        )
        # Register filters
        self.jinja_env.filters['date'] = format_date
        
    def _get_logo_data(self):
        """Read and encode the logo file as base64"""
        # Temporarily disabled logo functionality
        return None
        # try:
        #     logger.info(f"Attempting to read logo from path: {self.logo_path}")
        #     if not os.path.exists(self.logo_path):
        #         logger.error(f"Logo file does not exist at path: {self.logo_path}")
        #         return None
                
        #     with open(self.logo_path, 'rb') as f:
        #         image_data = f.read()
        #         encoded_data = f"data:image/png;base64,{base64.b64encode(image_data).decode()}"
        #         logger.info("Successfully encoded logo data")
        #         return encoded_data
        # except Exception as e:
        #     logger.error(f"Error reading logo file: {str(e)}")
        #     return None
        
    def _render_template(self, template_name: str, context: dict) -> str:
        template = self.jinja_env.get_template(template_name)
        context['service_name'] = settings.SERVICE_NAME
        context['service_url'] = settings.MAIN_APP_URL
        context['site_url'] = settings.SITE_URL
        context['logo_data'] = self._get_logo_data()
        context['current_year'] = datetime.now().year
        return template.render(**context)
        
    async def send_verification_email(self, email: str, code: str, verification_url: str = None):
        try:
            if verification_url is None:
                verification_url = f"{settings.SITE_URL}/verify?token={code}"
                
            message = Message(
                subject="Verify Your Email",
                html=self._render_template("verification.html", {
                    "code": code, 
                    "verification_url": verification_url,
                    "expiry_hours": settings.VERIFICATION_EXPIRY_HOURS
                }),
                mail_from=f'"{settings.SERVICE_NAME}" <{settings.SMTP_USER}>'
            )
            
            response = message.send(
                to=email,
                smtp={
                    "host": settings.SMTP_HOST, #"smtp-relay.gmail.com"
                    "port": settings.SMTP_PORT,
                    "user": settings.SMTP_USER,
                    "password": settings.SMTP_PASSWORD,
                    "tls": True
                }
            )
            
            self._log_email(email, "verification", "sent" if response.status_code == 250 else "failed")
            return response.status_code == 250
            
        except Exception as e:
            logger.error(f"Error sending verification email: {str(e)}")
            self._log_email(email, "verification", "failed", {"error": str(e)})
            return False

    async def send_subscription_receipt(self, email: str, subscription_data: dict):
        """Send a subscription receipt email"""
        try:
            message = Message(
                subject=f"Your {settings.SERVICE_NAME} {subscription_data['tier']} Plan Receipt",
                html=self._render_template("subscription_receipt.html", {
                    "email": email,
                    "subscription_data": subscription_data
                }),
                mail_from=f'"{settings.SERVICE_NAME}" <{settings.SMTP_USER}>'
            )
            
            response = message.send(
                to=email,
                smtp={
                    "host": settings.SMTP_HOST, #"smtp-relay.gmail.com"
                    "port": settings.SMTP_PORT,
                    "user": settings.SMTP_USER,
                    "password": settings.SMTP_PASSWORD,
                    "tls": True
                }
            )
            
            self._log_email(email, "subscription_receipt", "sent" if response.status_code == 250 else "failed")
            return response.status_code == 250
            
        except Exception as e:
            logger.error(f"Error sending subscription receipt email: {str(e)}")
            self._log_email(email, "subscription_receipt", "failed", {"error": str(e)})
            return False

    async def send_account_change_notification(self, email: str, subscription_data: dict):
        """Send an account change notification email"""
        try:
            message = Message(
                subject=f"Your {settings.SERVICE_NAME} Account Update",
                html=self._render_template("account_change.html", {
                    "email": email,
                    "subscription_data": subscription_data
                }),
                mail_from=f'"{settings.SERVICE_NAME}" <{settings.SMTP_USER}>'
            )
            
            response = message.send(
                to=email,
                smtp={
                    "host": settings.SMTP_HOST, #"smtp-relay.gmail.com"
                    "port": settings.SMTP_PORT,
                    "user": settings.SMTP_USER,
                    "password": settings.SMTP_PASSWORD,
                    "tls": True
                }
            )
            
            self._log_email(email, "account_change", "sent" if response.status_code == 250 else "failed")
            return response.status_code == 250
            
        except Exception as e:
            logger.error(f"Error sending account change email: {str(e)}")
            self._log_email(email, "account_change", "failed", {"error": str(e)})
            return False

    async def send_subscription_cancelled(self, email: str, subscription_data: dict):
        try:
            message = Message(
                subject=f"We'll Miss You at {settings.SERVICE_NAME}",
                html=self._render_template("subscription_cancelled.html", {
                    "email": email,
                    "subscription_data": subscription_data
                }),
                mail_from=f'"{settings.SERVICE_NAME}" <{settings.SMTP_USER}>'
            )
            
            response = message.send(
                to=email,
                smtp={
                    "host": settings.SMTP_HOST, #"smtp-relay.gmail.com"
                    "port": settings.SMTP_PORT,
                    "user": settings.SMTP_USER,
                    "password": settings.SMTP_PASSWORD,
                    "tls": True
                }
            )
            
            self._log_email(email, "subscription_cancelled", "sent" if response.status_code == 250 else "failed")
            return response.status_code == 250
            
        except Exception as e:
            logger.error(f"Error sending subscription cancellation email: {str(e)}")
            self._log_email(email, "subscription_cancelled", "failed", {"error": str(e)})
            return False
            
    def _log_email(self, email_to: str, email_type: str, status: str, meta_data: dict = None):
        log = EmailLog(
            email_to=email_to,
            email_type=email_type,
            status=status,
            meta_data=meta_data,
            sent_at=datetime.utcnow() if status == "sent" else None
        )
        self.db.add(log)
        self.db.commit()

    async def send_welcome_email(self, email: str, user_data: dict):
        """Send a welcome email for new users"""
        try:
            message = Message(
                subject=f"Welcome to the {settings.SERVICE_NAME} Family!",
                html=self._render_template("welcome.html", {
                    "email": email,
                    "user_data": user_data
                }),
                mail_from=f'"{settings.SERVICE_NAME}" <{settings.SMTP_USER}>'
            )
            
            response = message.send(
                to=email,
                smtp={
                    "host": settings.SMTP_HOST, #"smtp-relay.gmail.com"
                    "port": settings.SMTP_PORT,
                    "user": settings.SMTP_USER,
                    "password": settings.SMTP_PASSWORD,
                    "tls": True
                }
            )
            
            self._log_email(email, "welcome", "sent" if response.status_code == 250 else "failed")
            return response.status_code == 250
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {str(e)}")
            self._log_email(email, "welcome", "failed", {"error": str(e)})
            return False

    async def send_trial_expired_email(self, email: str, user_data: dict):
        """Send a trial expired email with re-engagement content"""
        try:
            message = Message(
                subject=f"Your {settings.SERVICE_NAME} Trial Has Expired",
                html=self._render_template("trial_expired.html", {
                    "email": email,
                    "user_data": user_data
                }),
                mail_from=f'"{settings.SERVICE_NAME}" <{settings.SMTP_USER}>'
            )
            
            response = message.send(
                to=email,
                smtp={
                    "host": settings.SMTP_HOST, #"smtp-relay.gmail.com",
                    "port": settings.SMTP_PORT,
                    "user": settings.SMTP_USER,
                    "password": settings.SMTP_PASSWORD,
                    "tls": True
                }
            )
            
            self._log_email(email, "trial_expired", "sent" if response.status_code == 250 else "failed")
            return response.status_code == 250
            
        except Exception as e:
            logger.error(f"Error sending trial expired email: {str(e)}")
            self._log_email(email, "trial_expired", "failed", {"error": str(e)})
            return False