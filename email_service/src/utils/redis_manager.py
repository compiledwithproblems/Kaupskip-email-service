from redis.asyncio import Redis
from ..config import settings
import logging
import json

logger = logging.getLogger(__name__)

class RedisManager:
    def __init__(self):
        logger.info("Initializing Redis connection...")
        
        try:
            self.redis = Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                health_check_interval=30
            )
            logger.info(f"Successfully connected to Redis at {settings.REDIS_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis = None
            
    def get_main_connection(self):
        if not self.redis:
            try:
                self.redis = Redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    health_check_interval=30
                )
            except Exception as e:
                logger.error(f"Failed to reconnect to Redis: {str(e)}")
        return self.redis