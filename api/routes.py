from flask import request, jsonify
from datetime import datetime
from munich_path.services import auth_service, goal_service
from munich_path.database import db_manager # For fetching user details in /api/user and progress data

def init_app_routes(app):
    """
    Initializes and registers all API routes with the given Flask app instance.
    Args:
        app (Flask): The Flask application instance.
    """

    @app.route('/api/login', methods=['POST'])
    def api_login():
        """
        API endpoint for user login.
        Expects JSON body with 'email' and 'password'.
        Returns a session token upon successful authentication.
        """
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        user_id, name, message = auth_service.authenticate_user(email, password)

        if user_id:
            session_token = auth_service.create_api_session(user_id)
            if session_token:
                return jsonify({
                    'success': True,
                    'session_token': session_token,
                    'user_id': user_id,
                    'name': name
                }), 200
            else:
                return jsonify({'error': 'Failed to create session token'}), 500
        else:
            return jsonify({'error': message or 'Invalid credentials'}), 401

    @app.route('/api/user/<int:user_id>', methods=['GET'])
    def api_get_user(user_id):
        """
        API endpoint to get user information.
        Requires a valid session token in the 'Authorization' header.
        """
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '')

        # Validate the session token to ensure the request is authorized
        validated_user_id = auth_service.validate_api_session(session_token)

        # Ensure the user requesting data matches the user_id in the URL
        if not validated_user_id or validated_user_id != user_id:
            return jsonify({'error': 'Invalid or unauthorized session'}), 401

        user = db_manager.get_user(user_id) # Fetch user from db_manager
        if user:
            # Return a subset of user data, avoid sensitive information
            return jsonify({
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'current_streak': user['current_streak'],
                'total_streak': user['total_streak'],
                'level': user['current_level'],
                'money_at_risk': user['money_at_risk'],
                'is_locked': user['is_locked'],
                'lock_end_date': user['lock_end_date']
            }), 200
        else:
            return jsonify({'error': 'User not found'}), 404

    @app.route('/api/checkin', methods=['POST'])
    def api_checkin():
        """
        API endpoint to submit daily goals.
        Requires a valid session token in the 'Authorization' header.
        Expects JSON body with daily goal metrics.
        """
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = auth_service.validate_api_session(session_token)

        if not user_id:
            return jsonify({'error': 'Invalid session'}), 401

        data = request.json
        german_hours = data.get('german_hours', 0.0)
        tech_hours = data.get('tech_hours', 0.0)
        applications_sent = data.get('applications_sent', 0)
        words_learned = data.get('words_learned', 0)

        # Call the goal service to log daily goals and handle streak/penalty logic
        success, message = goal_service.log_daily_goals(
            user_id, german_hours, tech_hours, applications_sent, words_learned
        )
        
        # Determine if goals were met from the message or by re-checking if needed
        goals_met = "goals not met" not in message.lower()

        if success:
            return jsonify({'success': True, 'goals_met': goals_met, 'message': message}), 200
        else:
            # If log_daily_goals returns False for success, it implies an internal error
            # or a failure to log, distinct from goals not being met.
            return jsonify({'success': False, 'goals_met': goals_met, 'error': message}), 500

    @app.route('/api/progress/<int:user_id>', methods=['GET'])
    def api_get_progress(user_id):
        """
        API endpoint to get user progress data (streak, achievements, penalties).
        Requires a valid session token in the 'Authorization' header.
        """
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '')

        validated_user_id = auth_service.validate_api_session(session_token)
        if not validated_user_id or validated_user_id != user_id:
            return jsonify({'error': 'Invalid or unauthorized session'}), 401

        streak_data = goal_service.get_streak_data_for_progress(user_id)
        achievements = goal_service.get_user_achievements_list(user_id)
        penalties = goal_service.get_user_penalties_list(user_id)

        # Convert Row objects to dictionaries for JSON serialization if necessary
        # (db_manager returns dict-like objects if row_factory is set to sqlite3.Row)
        streak_data_json = [dict(row) for row in streak_data]
        achievements_json = [dict(row) for row in achievements]
        penalties_json = [dict(row) for row in penalties]

        return jsonify({
            'streak_data': streak_data_json,
            'achievements': achievements_json,
            'penalties': penalties_json
        }), 200

    # Add more API routes here as needed for other functionalities (e.g., settings update)
      