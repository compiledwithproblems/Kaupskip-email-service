from redis import Redis
from datetime import datetime, timedelta
import secrets
import json
from typing import Optional
from ..config import settings

class VerificationService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        
    async def create_verification(self, user_id: str, email: str) -> str:
        code = secrets.token_urlsafe(32)
        
        verification_data = {
            "code": code,
            "email": email,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store in Redis with expiry
        key = f"kaupskip:verification:{user_id}"
        await self.redis.setex(
            key,
            settings.VERIFICATION_EXPIRY_HOURS * 3600,
            json.dumps(verification_data)
        )
        
        return code
        
    async def verify_code(self, user_id: str, code: str) -> bool:
        key = f"kaupskip:verification:{user_id}"
        data = await self.redis.get(key)
        
        if not data:
            return False
            
        try:
            verification_data = json.loads(data)
            if verification_data["code"] != code:
                return False
                
            # Publish verification event
            event_data = {
                "user_id": user_id,
                "verified": True,
                "email": verification_data["email"],
                "verified_at": datetime.utcnow().isoformat()
            }
            await self.redis.publish("kaupskip:verification", json.dumps(event_data))
            
            # Delete the verification data
            await self.redis.delete(key)
            return True
            
        except (json.JSONDecodeError, KeyError):
            return False