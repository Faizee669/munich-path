from datetime import datetime, timedelta
from munich_path.database import db_manager

def log_daily_goals(user_id, german_hours, tech_hours, applications_sent, words_learned):
    """
    Logs the user's daily progress for their goals.
    This function will also determine if the daily goals were met.
    Args:
        user_id (int): The ID of the user.
        german_hours (float): Hours spent on German study.
        tech_hours (float): Hours spent on tech development.
        applications_sent (int): Number of job applications sent.
        words_learned (int): Number of German words learned.
    Returns:
        bool: True if goals were successfully logged, False otherwise.
    """
    today = datetime.now().date()
    
    # Define daily goal minimums (could also be imported from config)
    required_german_hours = 2.0
    required_tech_hours = 3.0
    required_applications_sent = 5
    required_words_learned = 50

    goals_met = (
        german_hours >= required_german_hours and
        tech_hours >= required_tech_hours and
        applications_sent >= required_applications_sent and
        words_learned >= required_words_learned
    )
    
    checkin_completed = 1 if goals_met else 0

    success = db_manager.log_daily_goals_db(
        user_id, today, german_hours, tech_hours,
        applications_sent, words_learned, checkin_completed
    )

    if success:
        if goals_met:
            update_user_streak(user_id, streak_broken=False)
            return True, "Daily goals completed!"
        else:
            update_user_streak(user_id, streak_broken=True)
            add_penalty(user_id, 10.0, "Daily goals not met") # Add a penalty for missing goals
            return False, "Daily goals not met. App locked for 24 hours and penalty applied."
    return False, "Failed to log daily goals."


def check_daily_completion(user_id):
    """
    Checks if the user has completed their daily check-in for today.
    Args:
        user_id (int): The ID of the user.
    Returns:
        bool: True if daily check-in is completed, False otherwise.
    """
    today = datetime.now().date()
    return db_manager.get_daily_goal_completion_status(user_id, today)

def update_user_streak(user_id, streak_broken=False):
    """
    Updates the user's current and total streak.
    If streak_broken is True, resets current streak and locks the app for 24 hours.
    Args:
        user_id (int): The ID of the user.
        streak_broken (bool): True if the daily goals were not met, breaking the streak.
    Returns:
        bool: True if streak updated successfully, False otherwise.
    """
    user = db_manager.get_user(user_id)
    if not user:
        return False

    current_streak = user['current_streak']
    total_streak = user['total_streak']
    is_locked = user['is_locked']
    lock_end_date = None
    last_checkin = datetime.now().date() # Always update last_checkin on an action

    if streak_broken:
        current_streak = 0
        is_locked = 1
        lock_end_date = datetime.now().date() + timedelta(days=1)
        # Add penalty here if not already handled by log_daily_goals
    else:
        current_streak += 1
        total_streak += 1 # Total streak should always increment on successful check-in

    return db_manager.update_user_streak_data(
        user_id, current_streak, total_streak, is_locked, lock_end_date, last_checkin
    )

def add_penalty(user_id, amount, reason):
    """
    Adds a financial penalty for the user.
    Args:
        user_id (int): The ID of the user.
        amount (float): The amount of the penalty.
        reason (str): The reason for the penalty.
    Returns:
        bool: True if penalty added successfully, False otherwise.
    """
    today = datetime.now().date()
    return db_manager.add_penalty_db(user_id, amount, reason, today)

def add_achievement(user_id, achievement_name):
    """
    Awards an achievement to the user. Checks if it already exists to prevent duplicates.
    Args:
        user_id (int): The ID of the user.
        achievement_name (str): The name of the achievement.
    Returns:
        bool: True if achievement added, False if it already existed or failed.
    """
    today = datetime.now().date()
    return db_manager.add_achievement_db(user_id, achievement_name, today)

def unlock_app(user_id):
    """
    Unlocks the application for a user.
    Args:
        user_id (int): The ID of the user.
    Returns:
        bool: True if app unlocked successfully, False otherwise.
    """
    return db_manager.unlock_app_db(user_id)

def reset_streak_and_unlock(user_id):
    """
    Performs an emergency unlock, resetting the current streak and removing lock.
    Typically associated with a penalty.
    Args:
        user_id (int): The ID of the user.
    Returns:
        bool: True if successful, False otherwise.
    """
    return db_manager.reset_streak_and_unlock_db(user_id)

def get_user_achievements_list(user_id):
    """Retrieves a list of achievements for a user."""
    return db_manager.get_user_achievements(user_id)

def get_user_penalties_list(user_id):
    """Retrieves a list of pending penalties for a user."""
    return db_manager.get_user_penalties(user_id)

def get_streak_data_for_progress(user_id):
    """Retrieves daily activity data for progress visualization."""
    return db_manager.get_streak_data(user_id)
