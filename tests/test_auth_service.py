import unittest
import os
import sqlite3
from datetime import datetime, timedelta

# Import the modules to be tested and their dependencies
from munich_path.database import db_manager
from munich_path.services import auth_service
from munich_path.utils import helpers
from munich_path import config # To ensure config is loaded for email setup (though we'll mock email sending)

# Ensure environment variables are loaded for config if running tests directly
from dotenv import load_dotenv
load_dotenv()

class TestAuthService(unittest.TestCase):

    def setUp(self):
        """
        Set up a fresh in-memory SQLite database for each test to ensure isolation.
        We'll temporarily change the DATABASE_PATH in db_manager for testing.
        """
        self.original_db_path = db_manager.DATABASE_PATH
        db_manager.DATABASE_PATH = ':memory:' # Use in-memory database for testing
        
        # Initialize the database schema for the in-memory DB
        db_manager.init_database()

        # Mock the send_reset_email function to prevent actual emails from being sent during tests
        self.original_send_reset_email = helpers.send_reset_email
        helpers.send_reset_email = self.mock_send_reset_email_success
        self.email_sent_mock_calls = []

    def tearDown(self):
        """
        Clean up after each test: close the connection and restore original DB path.
        """
        # Close any open connections to the in-memory database if they exist
        conn = sqlite3.connect(db_manager.DATABASE_PATH)
        conn.close()
        
        # Restore the original database path
        db_manager.DATABASE_PATH = self.original_db_path

        # Restore the original send_reset_email function
        helpers.send_reset_email = self.original_send_reset_email

    def mock_send_reset_email_success(self, recipient_email, reset_token):
        """A mock function for send_reset_email that always returns True."""
        self.email_sent_mock_calls.append({'email': recipient_email, 'token': reset_token})
        return True
    
    def mock_send_reset_email_failure(self, recipient_email, reset_token):
        """A mock function for send_reset_email that always returns False."""
        return False

    def test_create_user_success(self):
        """Test successful user creation."""
        user_id, _, message = auth_service.create_user("test@example.com", "password123", "Test User", 50.0)
        self.assertIsNotNone(user_id)
        self.assertEqual(message, "Success")

        user = db_manager.get_user(user_id)
        self.assertIsNotNone(user)
        self.assertEqual(user['email'], "test@example.com")
        self.assertEqual(user['name'], "Test User")
        self.assertIsNotNone(user['password_hash'])
        self.assertEqual(user['money_at_risk'], 50.0)

    def test_create_user_duplicate_email(self):
        """Test creating a user with an email that already exists."""
        auth_service.create_user("duplicate@example.com", "password123", "User One")
        user_id, _, message = auth_service.create_user("duplicate@example.com", "password456", "User Two")
        self.assertIsNone(user_id)
        self.assertEqual(message, "Email already registered")

    def test_authenticate_user_success(self):
        """Test successful user authentication."""
        auth_service.create_user("login@example.com", "securepass", "Login User")
        user_id, name, message = auth_service.authenticate_user("login@example.com", "securepass")
        self.assertIsNotNone(user_id)
        self.assertEqual(name, "Login User")
        self.assertEqual(message, "Authentication successful")

    def test_authenticate_user_invalid_password(self):
        """Test authentication with an incorrect password."""
        auth_service.create_user("badpass@example.com", "correctpass", "Bad Pass User")
        user_id, name, message = auth_service.authenticate_user("badpass@example.com", "wrongpass")
        self.assertIsNone(user_id)
        self.assertIsNone(name)
        self.assertEqual(message, "Invalid email or password")

    def test_authenticate_user_not_found(self):
        """Test authentication for a user that does not exist."""
        user_id, name, message = auth_service.authenticate_user("nonexistent@example.com", "somepass")
        self.assertIsNone(user_id)
        self.assertIsNone(name)
        self.assertEqual(message, "Invalid email or password")
        
    def test_initiate_password_reset_success(self):
        """Test successful password reset initiation."""
        auth_service.create_user("reset@example.com", "oldpass", "Reset User")
        success, message = auth_service.initiate_password_reset("reset@example.com")
        self.assertTrue(success)
        self.assertEqual(message, "Password reset email sent. Check your inbox.")
        self.assertEqual(len(self.email_sent_mock_calls), 1)
        self.assertEqual(self.email_sent_mock_calls[0]['email'], "reset@example.com")
        
        user_data = db_manager.get_user_by_email("reset@example.com")
        self.assertIsNotNone(user_data['reset_token'])
        self.assertIsNotNone(user_data['reset_token_expires'])
        
        # Verify token expiry is in the future
        expires_at = datetime.strptime(user_data['reset_token_expires'], '%Y-%m-%d %H:%M:%S.%f')
        self.assertGreater(expires_at, datetime.now())

    def test_initiate_password_reset_email_not_found(self):
        """Test password reset initiation for a non-existent email."""
        success, message = auth_service.initiate_password_reset("noexist@example.com")
        self.assertFalse(success)
        self.assertEqual(message, "Email not found")
        self.assertEqual(len(self.email_sent_mock_calls), 0)

    def test_initiate_password_reset_email_send_failure(self):
        """Test password reset initiation when email sending fails."""
        auth_service.create_user("failmail@example.com", "oldpass", "Fail Mail User")
        
        # Temporarily change the mock to simulate email sending failure
        helpers.send_reset_email = self.mock_send_reset_email_failure
        
        success, message = auth_service.initiate_password_reset("failmail@example.com")
        self.assertFalse(success)
        self.assertEqual(message, "Failed to send reset email. Please try again.")
        self.assertEqual(len(self.email_sent_mock_calls), 0) # No email recorded by the success mock

    def test_reset_password_success(self):
        """Test successful password reset."""
        auth_service.create_user("resetme@example.com", "oldpass", "Reset Me")
        
        # Manually set a token for testing the reset_password function
        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        reset_token = helpers.generate_reset_token()
        expires_at = datetime.now() + timedelta(hours=1)
        cursor.execute('''
            UPDATE users SET reset_token = ?, reset_token_expires = ? WHERE email = ?
        ''', (reset_token, expires_at, "resetme@example.com"))
        conn.commit()
        conn.close()

        success, message = auth_service.reset_password("resetme@example.com", reset_token, "newstrongpass")
        self.assertTrue(success)
        self.assertEqual(message, "Password reset successfully")

        # Verify password now works with the new password
        user_id, name, msg = auth_service.authenticate_user("resetme@example.com", "newstrongpass")
        self.assertIsNotNone(user_id)
        self.assertEqual(msg, "Authentication successful")
        
        # Verify token and expiry are cleared
        user_data = db_manager.get_user_by_email("resetme@example.com")
        self.assertIsNone(user_data['reset_token'])
        self.assertIsNone(user_data['reset_token_expires'])

    def test_reset_password_invalid_token(self):
        """Test password reset with an invalid token."""
        auth_service.create_user("invalidtoken@example.com", "oldpass", "Invalid Token User")
        
        success, message = auth_service.reset_password("invalidtoken@example.com", "wrongtoken", "newpass")
        self.assertFalse(success)
        self.assertEqual(message, "Invalid or expired reset token.")

    def test_reset_password_expired_token(self):
        """Test password reset with an expired token."""
        auth_service.create_user("expiredtoken@example.com", "oldpass", "Expired Token User")
        
        # Manually set an expired token
        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        reset_token = helpers.generate_reset_token()
        expires_at = datetime.now() - timedelta(hours=1) # Set to 1 hour ago
        cursor.execute('''
            UPDATE users SET reset_token = ?, reset_token_expires = ? WHERE email = ?
        ''', (reset_token, expires_at, "expiredtoken@example.com"))
        conn.commit()
        conn.close()

        success, message = auth_service.reset_password("expiredtoken@example.com", reset_token, "newpass")
        self.assertFalse(success)
        self.assertEqual(message, "Invalid or expired reset token.")
        
    def test_create_api_session_success(self):
        """Test successful API session creation."""
        user_id, _, _ = auth_service.create_user("apisession@example.com", "pass", "API Session User")
        session_token = auth_service.create_api_session(user_id)
        self.assertIsNotNone(session_token)
        self.assertIsInstance(session_token, str)
        
        # Verify session exists in DB
        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, session_token FROM api_sessions WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['user_id'], user_id)
        self.assertEqual(result['session_token'], session_token)
        
    def test_validate_api_session_success(self):
        """Test successful API session validation."""
        user_id, _, _ = auth_service.create_user("validateapi@example.com", "pass", "Validate API User")
        session_token = auth_service.create_api_session(user_id)
        
        validated_id = auth_service.validate_api_session(session_token)
        self.assertEqual(validated_id, user_id)
        
    def test_validate_api_session_invalid_token(self):
        """Test API session validation with an invalid token."""
        validated_id = auth_service.validate_api_session("nonexistent_token")
        self.assertIsNone(validated_id)

    def test_validate_api_session_expired_token(self):
        """Test API session validation with an expired token."""
        user_id, _, _ = auth_service.create_user("expiredsession@example.com", "pass", "Expired Session User")
        session_token = auth_service.create_api_session(user_id)
        
        # Manually set session to expired
        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        expired_time = datetime.now() - timedelta(days=1)
        cursor.execute('UPDATE api_sessions SET expires_at = ? WHERE session_token = ?', 
                       (expired_time, session_token))
        conn.commit()
        conn.close()
        
        validated_id = auth_service.validate_api_session(session_token)
        self.assertIsNone(validated_id)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

