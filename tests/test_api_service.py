import unittest
import os
import json
import sqlite3
from datetime import datetime, timedelta

# Flask's testing client
from flask import Flask, jsonify

# Import the main Flask app instance and routes initialization
from munich_path.api.api import api_app as flask_test_app # Rename to avoid conflict with `app` in tests
from munich_path.api import routes

# Import services and db_manager to set up test data
from munich_path.database import db_manager
from munich_path.services import auth_service
from munich_path.services import goal_service

# Ensure environment variables are loaded for config if running tests directly
from dotenv import load_dotenv
load_dotenv()

class TestApiRoutes(unittest.TestCase):

    def setUp(self):
        """
        Set up a test client and an in-memory SQLite database for each test.
        """
        self.original_db_path = db_manager.DATABASE_PATH
        db_manager.DATABASE_PATH = ':memory:' # Use in-memory database for testing
        db_manager.init_database() # Initialize schema for the in-memory DB

        # Create a test client for the Flask app
        self.app = flask_test_app
        routes.init_app_routes(self.app) # Re-initialize routes with the test app context
        self.client = self.app.test_client()
        self.app.testing = True

        # Create a default test user for many tests
        self.user_email = "api_test_user@example.com"
        self.user_password = "api_secure_password"
        self.user_name = "API Test User"
        self.user_id, _, _ = auth_service.create_user(
            self.user_email, self.user_password, self.user_name
        )

    def tearDown(self):
        """
        Clean up after each test.
        """
        conn = sqlite3.connect(db_manager.DATABASE_PATH)
        conn.close()
        db_manager.DATABASE_PATH = self.original_db_path # Restore original DB path

    def create_and_authenticate_test_user(self, email, password):
        """Helper to create a user and get a session token."""
        user_id, _, _ = auth_service.create_user(email, password, f"User {email}")
        response = self.client.post('/api/login', json={'email': email, 'password': password})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        return user_id, data['session_token']

    # --- Test /api/login ---
    def test_api_login_success(self):
        """Test successful API login."""
        response = self.client.post('/api/login', json={
            'email': self.user_email,
            'password': self.user_password
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('session_token', data)
        self.assertEqual(data['user_id'], self.user_id)
        self.assertEqual(data['name'], self.user_name)

    def test_api_login_invalid_credentials(self):
        """Test API login with invalid password."""
        response = self.client.post('/api/login', json={
            'email': self.user_email,
            'password': 'wrong_password'
        })
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Invalid credentials')

    def test_api_login_missing_fields(self):
        """Test API login with missing email."""
        response = self.client.post('/api/login', json={
            'password': self.user_password
        })
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Email and password required')

    # --- Test /api/user/<int:user_id> ---
    def test_api_get_user_success(self):
        """Test getting user data successfully."""
        user_id, session_token = self.create_and_authenticate_test_user(
            "get_user@example.com", "getpass"
        )
        
        response = self.client.get(f'/api/user/{user_id}', headers={
            'Authorization': f'Bearer {session_token}'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['id'], user_id)
        self.assertEqual(data['email'], "get_user@example.com")
        self.assertEqual(data['name'], "User get_user@example.com")
        self.assertIn('current_streak', data)

    def test_api_get_user_invalid_session(self):
        """Test getting user data with invalid session token."""
        response = self.client.get(f'/api/user/{self.user_id}', headers={
            'Authorization': 'Bearer invalid_token'
        })
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invalid session')

    def test_api_get_user_not_found(self):
        """Test getting data for a non-existent user ID."""
        user_id, session_token = self.create_and_authenticate_test_user(
            "another_user@example.com", "anotherpass"
        )
        
        response = self.client.get('/api/user/99999', headers={
            'Authorization': f'Bearer {session_token}'
        })
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'User not found')

    # --- Test /api/checkin ---
    def test_api_checkin_success_goals_met(self):
        """Test successful daily check-in with goals met."""
        user_id, session_token = self.create_and_authenticate_test_user(
            "checkin_success@example.com", "checkpass"
        )
        
        response = self.client.post('/api/checkin', headers={
            'Authorization': f'Bearer {session_token}'
        }, json={
            'german_hours': 2.5,
            'tech_hours': 3.0,
            'applications_sent': 5,
            'words_learned': 50
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertTrue(data['goals_met'])
        self.assertIn('Daily goals completed', data['message'])
        
        # Verify streak updated in DB
        updated_user = db_manager.get_user(user_id)
        self.assertEqual(updated_user['current_streak'], 1)
        self.assertEqual(updated_user['is_locked'], 0) # Should not be locked

    def test_api_checkin_failure_goals_not_met(self):
        """Test daily check-in when goals are not met."""
        user_id, session_token = self.create_and_authenticate_test_user(
            "checkin_fail@example.com", "failpass"
        )
        
        response = self.client.post('/api/checkin', headers={
            'Authorization': f'Bearer {session_token}'
        }, json={
            'german_hours': 1.0, # Not enough
            'tech_hours': 1.0,   # Not enough
            'applications_sent': 1,
            'words_learned': 10
        })
        self.assertEqual(response.status_code, 200) # Checkin log is successful, but goal status is not
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertFalse(data['goals_met'])
        self.assertIn('Goals not met. App locked.', data['message'])
        
        # Verify streak broken and app locked in DB
        updated_user = db_manager.get_user(user_id)
        self.assertEqual(updated_user['current_streak'], 0)
        self.assertEqual(updated_user['is_locked'], 1)
        self.assertIsNotNone(updated_user['lock_end_date'])
        
        # Verify penalty added
        penalties = db_manager.get_user_penalties(user_id)
        self.assertGreater(len(penalties), 0)
        self.assertEqual(penalties[0]['amount'], 10.0)
        self.assertIn("Daily goals not met", penalties[0]['reason'])

    def test_api_checkin_invalid_session(self):
        """Test daily check-in with an invalid session token."""
        response = self.client.post('/api/checkin', headers={
            'Authorization': 'Bearer bogus_token'
        }, json={
            'german_hours': 2.0, 'tech_hours': 3.0, 'applications_sent': 5, 'words_learned': 50
        })
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invalid session')
        
    def test_api_checkin_missing_data(self):
        """Test daily check-in with missing data in the request body."""
        user_id, session_token = self.create_and_authenticate_test_user(
            "checkin_missing@example.com", "missingpass"
        )
        
        response = self.client.post('/api/checkin', headers={
            'Authorization': f'Bearer {session_token}'
        }, json={
            'german_hours': 2.5,
            # tech_hours, applications_sent, words_learned are missing
        })
        # Flask's request.json.get() will default to 0 for missing keys,
        # so this will be treated as goals not met. Status code should still be 200.
        self.assertEqual(response.status_code, 200) 
        data = json.loads(response.data)
        self.assertFalse(data['goals_met'])
        self.assertIn('Goals not met. App locked.', data['message'])

    # --- Test /api/progress/<int:user_id> ---
    def test_api_get_progress_success(self):
        """Test getting user progress data successfully."""
        user_id, session_token = self.create_and_authenticate_test_user(
            "progress_user@example.com", "progresspass"
        )
        
        # Add some mock data
        goal_service.log_daily_goals(user_id, 2.0, 3.0, 5, 50)
        goal_service.add_achievement(user_id, "Test Ach 1")
        goal_service.add_penalty(user_id, 15.0, "Test Penalty 1")

        response = self.client.get(f'/api/progress/{user_id}', headers={
            'Authorization': f'Bearer {session_token}'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('streak_data', data)
        self.assertIn('achievements', data)
        self.assertIn('penalties', data)
        
        self.assertGreater(len(data['streak_data']), 0)
        self.assertGreater(len(data['achievements']), 0)
        self.assertGreater(len(data['penalties']), 0)
        
        self.assertEqual(data['achievements'][0]['achievement_name'], "Test Ach 1")
        self.assertEqual(data['penalties'][0]['amount'], 15.0)


    def test_api_get_progress_invalid_session(self):
        """Test getting user progress data with invalid session token."""
        response = self.client.get(f'/api/progress/{self.user_id}', headers={
            'Authorization': 'Bearer another_bogus_token'
        })
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Invalid session')

    def test_api_get_progress_user_not_found(self):
        """Test getting progress for a non-existent user ID."""
        user_id, session_token = self.create_and_authenticate_test_user(
            "no_progress_user@example.com", "nopass"
        )
        
        response = self.client.get('/api/progress/99999', headers={
            'Authorization': f'Bearer {session_token}'
        })
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'User not found')


if __name__ == '__main__':
    # When running tests, Flask's app.run() is not used. Instead, the test client
    # directly interacts with the Flask app object.
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

