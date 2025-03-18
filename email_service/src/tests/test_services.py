import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from src.services.email_service import EmailService
from src.services.verification_service import VerificationService
from src.models.email_log import EmailLog
from src.utils.redis_manager import RedisManager

@pytest.fixture
def mock_db():
    return Mock(spec=Session)

@pytest.fixture
def mock_redis():
    return Mock(spec=RedisManager)

@pytest.fixture
def email_service(mock_db):
    return EmailService(mock_db)

@pytest.fixture
def verification_service(mock_redis):
    return VerificationService(mock_redis)

class TestEmailService:
    @patch('emails.Message')
    async def test_send_verification_email_success(self, mock_message, email_service, mock_db):
        # Arrange
        mock_message_instance = Mock()
        mock_message.return_value = mock_message_instance
        mock_message_instance.send.return_value.status_code = 250
        
        # Act
        result = await email_service.send_verification_email("test@example.com", "test-code")
        
        # Assert
        assert result is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
    @patch('emails.Message')
    async def test_send_verification_email_failure(self, mock_message, email_service, mock_db):
        # Arrange
        mock_message_instance = Mock()
        mock_message.return_value = mock_message_instance
        mock_message_instance.send.return_value.status_code = 500
        
        # Act
        result = await email_service.send_verification_email("test@example.com", "test-code")
        
        # Assert
        assert result is False
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
    def test_log_email(self, email_service, mock_db):
        # Act
        email_service._log_email("test@example.com", "verification", "sent")
        
        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        log_entry = mock_db.add.call_args[0][0]
        assert isinstance(log_entry, EmailLog)
        assert log_entry.email_to == "test@example.com"
        assert log_entry.email_type == "verification"
        assert log_entry.status == "sent"

class TestVerificationService:
    async def test_create_verification(self, verification_service, mock_redis):
        # Arrange
        user_id = "test-user"
        email = "test@example.com"
        
        # Act
        code = await verification_service.create_verification(user_id, email)
        
        # Assert
        assert code is not None
        mock_redis.setex.assert_called_once()
        key = f"verification:{user_id}"
        assert mock_redis.setex.call_args[0][0] == key
        
    async def test_verify_code_success(self, verification_service, mock_redis):
        # Arrange
        user_id = "test-user"
        code = "test-code"
        mock_redis.get.return_value = {"code": code}
        
        # Act
        result = await verification_service.verify_code(user_id, code)
        
        # Assert
        assert result is True
        mock_redis.delete.assert_called_once_with(f"verification:{user_id}")
        
    async def test_verify_code_failure(self, verification_service, mock_redis):
        # Arrange
        user_id = "test-user"
        code = "test-code"
        mock_redis.get.return_value = {"code": "different-code"}
        
        # Act
        result = await verification_service.verify_code(user_id, code)
        
        # Assert
        assert result is False
        mock_redis.delete.assert_not_called() 