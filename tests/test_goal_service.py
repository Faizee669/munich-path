import unittest
import os
import sqlite3
from datetime import datetime, timedelta

# Import the modules to be tested and their dependencies
from munich_path.database import db_manager
from munich_path.services import goal_service
from munich_path.services import auth_service # Needed to create a user for tests

class TestGoalService(unittest.TestCase):

    def setUp(self):
        """
        Set up a fresh in-memory SQLite database for each test.
        """
        self.original_db_path = db_manager.DATABASE_PATH
        db_manager.DATABASE_PATH = ':memory:' # Use in-memory database
        db_manager.init_database()

        # Create a test user for whom goals will be logged
        self.user_id, _, _ = auth_service.create_user(
            "test_goal_user@example.com", "goalpass123", "Goal Tester", 100.0
        )
        # Ensure the user object is updated with the latest from DB after creation
        self.user_data = db_manager.get_user(self.user_id)


    def tearDown(self):
        """
        Clean up after each test.
        """
        conn = sqlite3.connect(db_manager.DATABASE_PATH)
        conn.close()
        db_manager.DATABASE_PATH = self.original_db_path # Restore original DB path

    def test_log_daily_goals_success_first_checkin(self):
        """Test logging daily goals successfully for the first time in a day."""
        initial_streak = self.user_data['current_streak']
        success, message = goal_service.log_daily_goals(
            self.user_id, german_hours=2.0, tech_hours=3.0, applications_sent=5, words_learned=50
        )
        self.assertTrue(success)
        self.assertIn("Daily goals completed", message)

        # Verify entry in daily_goals table
        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_goals WHERE user_id = ? AND date = ?", 
                       (self.user_id, datetime.now().strftime('%Y-%m-%d')))
        goal_entry = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(goal_entry)
        self.assertEqual(goal_entry['german_hours'], 2.0)
        self.assertEqual(goal_entry['tech_hours'], 3.0)
        self.assertEqual(goal_entry['checkin_completed'], 1)

        # Verify streak update
        updated_user = db_manager.get_user(self.user_id)
        self.assertEqual(updated_user['current_streak'], initial_streak + 1)
        self.assertEqual(updated_user['total_streak'], initial_streak + 1)
        self.assertEqual(updated_user['is_locked'], 0) # Should not be locked

    def test_log_daily_goals_success_update_existing_checkin(self):
        """Test updating an existing daily goal entry on the same day."""
        # First check-in (partial)
        goal_service.log_daily_goals(
            self.user_id, german_hours=1.0, tech_hours=1.0, applications_sent=1, words_learned=10
        )
        
        # Second check-in (completing goals)
        success, message = goal_service.log_daily_goals(
            self.user_id, german_hours=2.0, tech_hours=3.0, applications_sent=5, words_learned=50
        )
        self.assertTrue(success)
        self.assertIn("Daily goals completed", message)

        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT german_hours, tech_hours, checkin_completed FROM daily_goals WHERE user_id = ? AND date = ?", 
                       (self.user_id, datetime.now().strftime('%Y-%m-%d')))
        goal_entry = cursor.fetchone()
        conn.close()

        self.assertEqual(goal_entry['german_hours'], 2.0)
        self.assertEqual(goal_entry['tech_hours'], 3.0)
        self.assertEqual(goal_entry['checkin_completed'], 1)
        
        # Streak should still be updated only once for the day if goals are met
        updated_user = db_manager.get_user(self.user_id)
        self.assertEqual(updated_user['current_streak'], self.user_data['current_streak'] + 1)

    def test_log_daily_goals_failure_not_met(self):
        """Test logging daily goals where requirements are not met."""
        initial_streak = self.user_data['current_streak']
        initial_is_locked = self.user_data['is_locked']

        success, message = goal_service.log_daily_goals(
            self.user_id, german_hours=1.0, tech_hours=1.0, applications_sent=1, words_learned=10
        )
        self.assertTrue(success) # The log itself is successful, but goals not met
        self.assertIn("goals not met", message)
        
        # Verify streak broken and app locked
        updated_user = db_manager.get_user(self.user_id)
        self.assertEqual(updated_user['current_streak'], 0)
        self.assertEqual(updated_user['is_locked'], 1)
        self.assertIsNotNone(updated_user['lock_end_date'])
        
        # Verify penalty added
        penalties = db_manager.get_user_penalties(self.user_id)
        self.assertGreater(len(penalties), 0)
        self.assertEqual(penalties[0]['amount'], 10.0)
        self.assertIn("Daily goals not met", penalties[0]['reason'])


    def test_check_daily_completion_true(self):
        """Test checking daily completion when goals are logged."""
        goal_service.log_daily_goals(self.user_id, 1.0, 1.0, 1, 1) # Log something for today
        self.assertTrue(goal_service.check_daily_completion(self.user_id))

    def test_check_daily_completion_false(self):
        """Test checking daily completion when no goals are logged for today."""
        self.assertFalse(goal_service.check_daily_completion(self.user_id))

    def test_add_penalty_success(self):
        """Test adding a penalty."""
        success = goal_service.add_penalty(self.user_id, 25.0, "Late payment")
        self.assertTrue(success)

        penalties = db_manager.get_user_penalties(self.user_id)
        self.assertEqual(len(penalties), 1)
        self.assertEqual(penalties[0]['amount'], 25.0)
        self.assertEqual(penalties[0]['reason'], "Late payment")
        self.assertEqual(penalties[0]['paid'], 0)

    def test_add_achievement_success(self):
        """Test adding a new achievement."""
        success = goal_service.add_achievement(self.user_id, "First Step")
        self.assertTrue(success)

        achievements = db_manager.get_user_achievements(self.user_id)
        self.assertEqual(len(achievements), 1)
        self.assertEqual(achievements[0]['achievement_name'], "First Step")

    def test_add_achievement_duplicate(self):
        """Test adding a duplicate achievement (should return False)."""
        goal_service.add_achievement(self.user_id, "First Step")
        success = goal_service.add_achievement(self.user_id, "First Step")
        self.assertFalse(success) # Should not add duplicate

        achievements = db_manager.get_user_achievements(self.user_id)
        self.assertEqual(len(achievements), 1) # Still only one entry

    def test_get_user_achievements_list(self):
        """Test retrieving user achievements."""
        goal_service.add_achievement(self.user_id, "Ach One")
        goal_service.add_achievement(self.user_id, "Ach Two")
        
        achievements = goal_service.get_user_achievements_list(self.user_id)
        self.assertEqual(len(achievements), 2)
        self.assertIn("Ach One", [a['achievement_name'] for a in achievements])
        self.assertIn("Ach Two", [a['achievement_name'] for a in achievements])

    def test_get_user_penalties_list(self):
        """Test retrieving user penalties."""
        goal_service.add_penalty(self.user_id, 10.0, "Missed Goal")
        goal_service.add_penalty(self.user_id, 5.0, "Late Check-in")
        
        penalties = goal_service.get_user_penalties_list(self.user_id)
        self.assertEqual(len(penalties), 2)
        self.assertEqual(penalties[0]['amount'], 10.0)
        self.assertEqual(penalties[1]['amount'], 5.0)

    def test_get_streak_data_for_progress(self):
        """Test retrieving streak data for progress visualization."""
        today = datetime.now().date()
        # Log some data for the last few days
        db_manager.log_daily_goals_db(self.user_id, (today - timedelta(days=2)).strftime('%Y-%m-%d'), 1.5, 2.0, 3, 30)
        db_manager.log_daily_goals_db(self.user_id, (today - timedelta(days=1)).strftime('%Y-%m-%d'), 2.5, 3.5, 6, 60)
        db_manager.log_daily_goals_db(self.user_id, today.strftime('%Y-%m-%d'), 2.0, 3.0, 5, 50)
        
        streak_data = goal_service.get_streak_data_for_progress(self.user_id)
        self.assertEqual(len(streak_data), 3)
        
        # Verify the content and order (should be descending by date in db_manager)
        self.assertEqual(streak_data[0]['date'], today.strftime('%Y-%m-%d'))
        self.assertEqual(streak_data[0]['german_hours'], 2.0)
        self.assertEqual(streak_data[2]['date'], (today - timedelta(days=2)).strftime('%Y-%m-%d'))


    def test_unlock_app_success(self):
        """Test unlocking the application."""
        # First, lock the app
        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_locked = 1, lock_end_date = ? WHERE id = ?",
                       ((datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d'), self.user_id))
        conn.commit()
        conn.close()

        success = goal_service.unlock_app(self.user_id)
        self.assertTrue(success)

        updated_user = db_manager.get_user(self.user_id)
        self.assertEqual(updated_user['is_locked'], 0)
        self.assertIsNone(updated_user['lock_end_date'])

    def test_reset_streak_and_unlock(self):
        """Test resetting streak and unlocking the app."""
        # Set a current streak and lock the app
        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET current_streak = 5, is_locked = 1, lock_end_date = ? WHERE id = ?",
                       ((datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d'), self.user_id))
        conn.commit()
        conn.close()

        success = goal_service.reset_streak_and_unlock(self.user_id)
        self.assertTrue(success)

        updated_user = db_manager.get_user(self.user_id)
        self.assertEqual(updated_user['current_streak'], 0)
        self.assertEqual(updated_user['is_locked'], 0)
        self.assertIsNone(updated_user['lock_end_date'])


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
