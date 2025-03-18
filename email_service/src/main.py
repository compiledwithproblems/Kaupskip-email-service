from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
import logging
import asyncio
from sqlalchemy import text

from src.database import get_db, init_db
from src.schemas.email import EmailVerificationRequest, EmailVerificationResponse, EmailLogResponse
from src.services.email_service import EmailService
from src.services.verification_service import VerificationService
from src.services.redis_subscriber import RedisSubscriber
from src.utils.redis_manager import RedisManager
from src.models.email_log import EmailLog
from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.SERVICE_NAME, version=settings.VERSION)

# Store background tasks for cleanup
background_tasks = set()
redis_subscriber = None

# Dependency Injection
def get_redis():
    return RedisManager()

def get_verification_service(redis: RedisManager = Depends(get_redis)):
    return VerificationService(redis.get_main_connection())

def get_email_service(db: Session = Depends(get_db)):
    return EmailService(db)

@app.on_event("startup")
async def startup_event():
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized")
        
        # Start Redis subscriber in the background
        redis_manager = RedisManager()
        connection = redis_manager.get_main_connection()
        try:
            await connection.execute_command('PING')
            logger.info("Redis connection successful")
        except Exception as redis_error:
            logger.error(f"Redis connection failed: {str(redis_error)}")
            raise
        
        db = next(get_db())
        email_service = EmailService(db)
        global redis_subscriber
        redis_subscriber = RedisSubscriber(redis_manager, email_service)
        
        # Start listening in the background
        task = asyncio.create_task(redis_subscriber.start_listening())
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)
        logger.info("Started Redis subscriber")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        # Don't raise the exception - allow the app to start without Redis
        # This enables the health endpoint to still work

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application...")
    
    # Stop Redis subscriber
    if redis_subscriber:
        logger.info("Stopping Redis subscriber...")
        await redis_subscriber.stop()
    
    # Cancel all background tasks
    for task in background_tasks:
        logger.info("Cancelling background task...")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    logger.info("Application shutdown complete")

@app.get("/health")
async def health_check():
    """Health check endpoint for container health monitoring"""
    return {
        "status": "healthy"
    }

@app.post("/verify/email", response_model=EmailVerificationResponse)
async def request_email_verification(
    request: EmailVerificationRequest,
    verification_service: VerificationService = Depends(get_verification_service),
    email_service: EmailService = Depends(get_email_service)
):
    try:
        # Generate verification code
        verification_code = await verification_service.create_verification(
            request.user_id,
            request.email
        )
        
        # Send verification email
        success = await email_service.send_verification_email(
            request.email,
            verification_code
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email"
            )
            
        return EmailVerificationResponse(
            success=True,
            message="Verification email sent successfully"
        )
        
    except Exception as e:
        logger.error(f"Error in email verification request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/verify/status/{user_id}")
async def check_verification_status(
    user_id: str,
    code: str,
    verification_service: VerificationService = Depends(get_verification_service)
):
    try:
        is_verified = await verification_service.verify_code(user_id, code)
        return {"verified": is_verified}
    except Exception as e:
        logger.error(f"Error checking verification status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/logs/email", response_model=List[EmailLogResponse])
async def get_email_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    try:
        logs = db.query(EmailLog).offset(skip).limit(limit).all()
        return logs
    except Exception as e:
        logger.error(f"Error retrieving email logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"}
    ) 