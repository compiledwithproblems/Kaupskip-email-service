from fastapi import FastAPI, HTTPException
from emails import Message
from typing import Optional, Literal
from pydantic import BaseModel
import logging
from ..config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

class EmailTestRequest(BaseModel):
    to_email: str
    template_name: Literal["welcome", "verification", "trial_expired", "subscription_receipt", "subscription_cancelled"]
    test_data: Optional[dict] = None

@app.post("/test-email")
async def send_test_email(request: EmailTestRequest):
    try:
        # Create a basic test data if none provided
        test_data = request.test_data or {
            "email": request.to_email,
            "user_data": {
                "characters": [
                    {
                        "name": "Test Character",
                        "personality": "A friendly test character for email template verification"
                    }
                ],
                "total_characters": 1
            },
            "subscription_data": {
                "tier": "Premium",
                "price": "9.99",
                "billing_period": "monthly"
            },
            "verification_url": f"{settings.SITE_URL}/verify?token=test",
            "code": "TEST123",
            "expiry_hours": settings.VERIFICATION_EXPIRY_HOURS
        }

        # Load the appropriate template
        from jinja2 import Environment, FileSystemLoader
        import os

        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        jinja_env = Environment(loader=FileSystemLoader(template_dir))
        template = jinja_env.get_template(f"{request.template_name}.html")

        # Add common template variables
        test_data.update({
            "service_name": settings.SERVICE_NAME,
            "service_url": settings.MAIN_APP_URL,
            "site_url": settings.SITE_URL,
            "current_year": 2024  # You might want to make this dynamic
        })

        # Render the template
        html_content = template.render(**test_data)

        # Create and send the email
        message = Message(
            subject=f"Test Email - {request.template_name.replace('_', ' ').title()}",
            html=html_content,
            mail_from=f'"{settings.SERVICE_NAME}" <{settings.SMTP_USER}>'
        )

        response = message.send(
            to=request.to_email,
            smtp={
                "host": settings.SMTP_HOST,
                "port": settings.SMTP_PORT,
                "user": settings.SMTP_USER,
                "password": settings.SMTP_PASSWORD,
                "tls": True
            }
        )

        if response.status_code == 250:
            return {
                "success": True,
                "message": f"Test email ({request.template_name}) sent successfully to {request.to_email}"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send email. SMTP Status: {response.status_code}"
            )

    except Exception as e:
        logger.error(f"Error sending test email: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test email: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
