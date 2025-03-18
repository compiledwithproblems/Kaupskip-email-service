import json
import logging
from redis import Redis
from .email_service import EmailService
from ..config import settings

logger = logging.getLogger(__name__)

class RedisSubscriber:
    def __init__(self, redis_manager, email_service: EmailService):
        logger.info("Initializing Redis subscriber...")
        self.redis = redis_manager.get_main_connection()
        self.email_service = email_service
        self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
        self._running = False
        logger.info("Redis subscriber initialized successfully")

    async def start_listening(self):
        try:
            logger.info("Starting Redis subscriber for main API events...")
            logger.info("Subscribing to channels: user_registration, kaupskip:subscription, kaupskip:marketing")
            await self.pubsub.subscribe("user_registration", "kaupskip:subscription", "kaupskip:marketing")
            
            self._running = True
            logger.info("Starting message loop...")
            while self._running:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    try:
                        logger.debug(f"Received raw message: {message}")
                        
                        if message["type"] == "message":
                            data = json.loads(message["data"])
                            channel = message["channel"]
                            if isinstance(channel, bytes):
                                channel = channel.decode("utf-8")
                            
                            if channel == "user_registration":
                                logger.info(f"Received registration event from main API: {data}")
                                
                                # Validate required fields
                                if not all(k in data for k in ["user_id", "email", "verification_token", "verification_url"]):
                                    logger.error(f"Missing required fields in message: {data}")
                                    continue
                                
                                # Send verification email
                                logger.info(f"Sending verification email to {data['email']}")
                                await self.email_service.send_verification_email(
                                    email=data["email"],
                                    code=data["verification_token"],
                                    verification_url=data["verification_url"]
                                )
                                logger.info(f"Successfully processed registration event for {data['email']}")
                                
                            elif channel == "kaupskip:subscription":
                                logger.info(f"Received subscription event: {data}")
                                
                                # Validate subscription event fields
                                if not all(k in data for k in ["user_id", "email", "tier", "subscription_data"]):
                                    logger.error(f"Missing required fields in subscription event: {data}")
                                    continue
                                    
                                try:
                                    await self._handle_subscription_event(data)
                                except Exception as e:
                                    logger.error(f"Error processing subscription event: {str(e)}")
                                
                            elif channel == "kaupskip:marketing":
                                logger.info(f"Received marketing event: {data}")
                                
                                # Validate marketing event fields
                                if not all(k in data for k in ["event_type", "data"]):
                                    logger.error(f"Missing required fields in marketing event: {data}")
                                    continue
                                    
                                try:
                                    await self._handle_marketing_event(data)
                                except Exception as e:
                                    logger.error(f"Error processing marketing event: {str(e)}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode message data: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}")
                        logger.error(f"Message that caused error: {message}")
                        
        except Exception as e:
            logger.error(f"Fatal error in Redis subscription: {str(e)}")
            raise

    async def stop(self):
        """Gracefully stop the subscriber"""
        logger.info("Stopping Redis subscriber...")
        self._running = False
        self.pubsub.unsubscribe()
        self.pubsub.close()
        logger.info("Redis subscriber stopped successfully") 

    async def _handle_subscription_event(self, data: dict):
        """Handle subscription-related events"""
        event_type = data.get('event_type')
        email = data.get('email')
        subscription_data = data.get('subscription_data', {})

        if not email:
            logger.error("No email provided in subscription event")
            return

        try:
            logger.info(f"Processing {event_type} for user {email}")
            
            if event_type == 'subscription_created':
                await self.email_service.send_subscription_receipt(email, subscription_data)
            elif event_type == 'subscription_cancelled':
                await self.email_service.send_subscription_cancelled(email, subscription_data)
            elif event_type == 'subscription_downgraded':
                # Handle downgrade event with account change notification
                await self.email_service.send_account_change_notification(email, subscription_data)
            else:
                logger.warning(f"Unknown subscription event type: {event_type}")
        except Exception as e:
            logger.error(f"Error processing subscription event: {str(e)}") 

    async def _handle_marketing_event(self, data: dict):
        """Handle marketing-related events"""
        event_type = data.get('event_type')
        user_data = data.get('data', {})
        email = user_data.get('email')

        if not email:
            logger.error("No email provided in marketing event")
            return

        try:
            logger.info(f"Processing marketing event {event_type} for user {email}")
            
            if event_type == 'marketing:oauth_signup' or event_type == 'marketing:email_verified':
                await self.email_service.send_welcome_email(email, user_data)
            elif event_type == 'marketing:trial_expired':
                await self.email_service.send_trial_expired_email(email, user_data)
            else:
                logger.warning(f"Unknown marketing event type: {event_type}")
        except Exception as e:
            logger.error(f"Error processing marketing event: {str(e)}") 