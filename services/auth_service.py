import hashlib
import secrets
from datetime import datetime, timedelta

from munich_path.database import db_manager
from munich_path.utils import helpers # For email validation, hashing, email sending

def create_user(email, password, name, money_at_risk=0.0, gemini_api_key=None):
    """
    Registers a new user.
    Args:
        email (str): User's email address (must be unique).
        password (str): User's raw password.
        name (str): User's full name.
        money_at_risk (float): Optional amount of money at risk for goals.
        gemini_api_key (str): Optional Gemini API key for AI features.
    Returns:
        tuple: (user_id, message) if successful, (None, error_message) otherwise.
    """
    if not helpers.validate_email(email):
        return None, "Invalid email format."

    # Check if user already exists
    existing_user = db_manager.get_user_by_email(email)
    if existing_user:
        return None, "Email already registered."

    password_hash = helpers.hash_password(password)
    start_date = datetime.now().date()

    user_id = db_manager.create_user_db(email, password_hash, name, start_date, money_at_risk, gemini_api_key)

    if user_id:
        return user_id, "Success"
    else:
        return None, "Failed to create user account."

def authenticate_user(email, password):
    """
    Authenticates a user based on email and password.
    Args:
        email (str): User's email address.
        password (str): User's raw password.
    Returns:
        tuple: (user_id, name) if authentication successful, (None, None) otherwise.
    """
    user = db_manager.get_user_by_email(email)
    if user and helpers.verify_password(password, user['password_hash']):
        # Update last login time
        db_manager.update_user_login_time(user['id'])
        return user['id'], user['name']
    return None, None

def initiate_password_reset(email):
    """
    Initiates the password reset process by generating and sending a token.
    Args:
        email (str): The email address of the user requesting a reset.
    Returns:
        tuple: (bool, str) True and success message if email sent, False and error message otherwise.
    """
    user = db_manager.get_user_by_email(email)
    if not user:
        return False, "Email not found."

    reset_token = helpers.generate_reset_token()
    expires_at = datetime.now() + timedelta(hours=1) # Token valid for 1 hour

    if db_manager.store_reset_token(email, reset_token, expires_at):
        if helpers.send_reset_email(email, reset_token):
            return True, "Password reset email sent. Check your inbox."
        else:
            # If email sending fails, clear the token as it's not usable
            db_manager.clear_reset_token(email)
            return False, "Failed to send reset email. Please try again later."
    else:
        return False, "Failed to generate reset token. Please try again."

def reset_password(email, reset_token, new_password):
    """
    Resets a user's password using a valid reset token.
    Args:
        email (str): User's email.
        reset_token (str): The reset token received by email.
        new_password (str): The new password for the user.
    Returns:
        tuple: (bool, str) True and success message if password reset, False and error message otherwise.
    """
    token_info = db_manager.get_reset_token_info(email, reset_token)

    if not token_info:
        return False, "Invalid reset token."

    # Convert stored expiry string back to datetime object
    expires_at = datetime.strptime(token_info['reset_token_expires'], '%Y-%m-%d %H:%M:%S')

    if datetime.now() > expires_at:
        db_manager.clear_reset_token(email) # Clear expired token
        return False, "Reset token has expired."

    new_password_hash = helpers.hash_password(new_password)

    if db_manager.update_user_password(email, new_password_hash):
        db_manager.clear_reset_token(email) # Clear token after successful use
        return True, "Password reset successfully. You can now log in with your new password."
    else:
        return False, "Failed to reset password."
