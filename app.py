import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import json # Used for API documentation display

# Import modules from the new structure
from munich_path.config import EMAIL_CONFIG, GEMINI_AVAILABLE
from munich_path.database import db_manager
from munich_path.services import auth_service, goal_service, ai_service
from munich_path.utils import helpers

# Optional: If you want to start the API from Streamlit (for local testing convenience)
# In a real deployment, the API would likely be a separate service.
# For demonstration purposes, we will keep the Flask API import here,
# but note that running a server in a Streamlit app is generally not recommended
# for production. The API documentation will remain regardless.
import threading
from munich_path.api import api as flask_api_app_module # Import the Flask app object and run function

# Initialize session state (important for Streamlit)
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'db_initialized' not in st.session_state:
    st.session_state.db_initialized = False
if 'api_running' not in st.session_state:
    st.session_state.api_running = False # State to track if Flask API thread is running

# Configure Gemini state
if 'gemini_configured' not in st.session_state:
    st.session_state.gemini_configured = False
if 'gemini_model_name' not in st.session_state:
    st.session_state.gemini_model_name = 'gemini-1.5-flash'


# --- Streamlit Page Functions ---

def login_page():
    """Renders the login, registration, and password reset forms."""
    st.title("🚀 Munich Path - Login")

    tab1, tab2, tab3 = st.tabs(["Login", "Register", "Reset Password"])

    with tab1:
        st.subheader("Login to Your Account")
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="your.email@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password")
            elif not helpers.validate_email(email):
                st.error("Please enter a valid email address")
            else:
                user_id, name = auth_service.authenticate_user(email, password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.session_state.page = 'dashboard'
                    st.success(f"Welcome back, {name}!")
                    st.rerun()
                else:
                    st.error("Invalid email or password")

    with tab2:
        st.subheader("Create New Account")
        with st.form("register_form"):
            reg_email = st.text_input("Email", placeholder="your.email@example.com", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password")
            name = st.text_input("Full Name", placeholder="Your full name")
            money_at_risk = st.number_input("Money at Risk ($)", min_value=0.0, max_value=1000.0,
                                           value=100.0, step=10.0,
                                           help="This money will be at risk if you fail to meet daily goals")

            if GEMINI_AVAILABLE:
                st.write("🤖 *Optional* - Gemini API Key for AI features")
                with st.expander("ℹ️ How to get a Gemini API Key"):
                    st.write("""
                    1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
                    2. Sign in with your Google account
                    3. Click "Create API Key"
                    4. Copy the API key and paste it below
                    """)
                gemini_api_key = st.text_input("Gemini API Key", type="password", key="reg_gemini")
            else:
                gemini_api_key = None
                st.info("💡 Install `google-generativeai` to enable AI features")

            register_submitted = st.form_submit_button("Create Account")

        if register_submitted:
            if not all([reg_email, reg_password, confirm_password, name]):
                st.error("Please fill in all required fields")
            elif not helpers.validate_email(reg_email):
                st.error("Please enter a valid email address")
            elif len(reg_password) < 6:
                st.error("Password must be at least 6 characters long")
            elif reg_password != confirm_password:
                st.error("Passwords do not match")
            else:
                user_id, message = auth_service.create_user(reg_email, reg_password, name, money_at_risk, gemini_api_key)
                if user_id:
                    st.success(f"Account created successfully! Welcome, {name}!")
                    st.session_state.user_id = user_id
                    st.session_state.page = 'dashboard'
                    st.rerun()
                else:
                    st.error(message)

    with tab3:
        st.subheader("Reset Password")
        reset_step = st.radio("Select step:", ["Request Reset", "Enter Reset Token"])

        if reset_step == "Request Reset":
            with st.form("reset_request_form"):
                reset_email = st.text_input("Email", placeholder="your.email@example.com")
                reset_submitted = st.form_submit_button("Send Reset Email")

            if reset_submitted:
                if not reset_email or not helpers.validate_email(reset_email):
                    st.error("Please enter a valid email address")
                else:
                    success, message = auth_service.initiate_password_reset(reset_email)
                    if success:
                        st.success("Reset email sent! Check your inbox.")
                    else:
                        st.error(message)

        else:
            with st.form("reset_token_form"):
                token_email = st.text_input("Email", placeholder="your.email@example.com")
                reset_token = st.text_input("Reset Token", placeholder="Token from email")
                new_password = st.text_input("New Password", type="password")
                confirm_new_password = st.text_input("Confirm New Password", type="password")
                token_submitted = st.form_submit_button("Reset Password")

            if token_submitted:
                if not all([token_email, reset_token, new_password, confirm_new_password]):
                    st.error("Please fill in all fields")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long")
                elif new_password != confirm_new_password:
                    st.error("Passwords do not match")
                else:
                    success, message = auth_service.reset_password(token_email, reset_token, new_password)
                    if success:
                        st.success("Password reset successfully! You can now login.")
                    else:
                        st.error(message)

def dashboard_page():
    """Displays the user's dashboard with key metrics, check-in status, achievements, and penalties."""
    # Get user data using db_manager
    user = db_manager.get_user(st.session_state.user_id)
    if not user:
        st.error("User not found. Please login again.")
        st.session_state.user_id = None
        st.session_state.page = 'login'
        st.rerun()
        return

    # Check lock status (using indices based on the user tuple from db_manager)
    if user['is_locked'] == 1:
        lock_end = user['lock_end_date']
        if lock_end:
            try:
                lock_end_date = datetime.strptime(lock_end, '%Y-%m-%d').date()
                if datetime.now().date() < lock_end_date:
                    lock_page()
                    return
            except ValueError:
                # If date format is wrong, unlock to prevent permanent lock
                goal_service.unlock_app(st.session_state.user_id)
                st.warning("Lock date format error, app unlocked. Please contact support.")

    st.title(f"👋 Welcome back, {user['name']}!")

    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔥 Current Streak", f"{user['current_streak']} days")
    with col2:
        st.metric("🏆 Total Streak", f"{user['total_streak']} days")
    with col3:
        st.metric("💰 At Risk", f"${user['money_at_risk']}")
    with col4:
        st.metric("🏅 Level", user['current_level'])

    # Check if daily check-in is completed
    if goal_service.check_daily_completion(st.session_state.user_id):
        st.success("✅ Daily check-in completed! Great job!")
    else:
        st.warning("⚠️ Daily check-in not completed yet")
        if st.button("Complete Daily Check-in"):
            st.session_state.page = 'checkin'
            st.rerun()

    # German practice section
    if user['gemini_api_key'] and GEMINI_AVAILABLE:
        st.subheader("📚 German Practice")
        if st.button("Practice German with AI"):
            st.session_state.page = 'german_practice'
            st.rerun()

    # Achievements
    achievements = goal_service.get_user_achievements(st.session_state.user_id)
    if achievements:
        st.subheader("🏆 Recent Achievements")
        for ach in achievements[:5]: # Display top 5 recent achievements
            st.markdown(f"**{ach['achievement_name']}** - {ach['date_earned']}")

    # Penalties
    penalties = goal_service.get_user_penalties(st.session_state.user_id)
    if penalties:
        st.subheader("💰 Pending Penalties")
        total_penalty = sum([p['amount'] for p in penalties])
        for pen in penalties:
            st.markdown(f"**${pen['amount']}** - {pen['reason']} ({pen['date']})")
        st.markdown(f"**Total Pending: ${total_penalty}**")

    # Navigation buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📊 Detailed Progress"):
            st.session_state.page = 'progress'
            st.rerun()
    with col2:
        if st.button("🎯 Daily Check-in"):
            st.session_state.page = 'checkin'
            st.rerun()
    with col3:
        if st.button("🇩🇪 German Practice"):
            st.session_state.page = 'german_practice'
            st.rerun()
    with col4:
        if st.button("⚙️ Settings"):
            st.session_state.page = 'settings'
            st.rerun()


def checkin_page():
    """Allows users to submit their daily goals and tracks streak."""
    st.title("✅ Daily Munich Path Check-in")

    # Check if already completed
    if goal_service.check_daily_completion(st.session_state.user_id):
        st.success("✅ Daily check-in already completed today!")
        if st.button("Back to Dashboard"):
            st.session_state.page = 'dashboard'
            st.rerun()
        return

    st.write("Complete your daily Munich Path requirements:")

    with st.form("daily_checkin_form"):
        col1, col2 = st.columns(2)
        with col1:
            german_hours = st.number_input("Hours of German study", min_value=0.0, max_value=24.0, value=0.0, step=0.5)
            tech_hours = st.number_input("Hours of tech development", min_value=0.0, max_value=24.0, value=0.0, step=0.5)
        with col2:
            apps_sent = st.number_input("Job applications sent", min_value=0, max_value=50, value=0, step=1)
            words_learned = st.number_input("German words learned", min_value=0, max_value=1000, value=0, step=10)

        submitted = st.form_submit_button("Submit Daily Check-in")

    if submitted:
        goal_met = (german_hours >= 2.0 and tech_hours >= 3.0 and apps_sent >= 5 and words_learned >= 50)

        if goal_met:
            st.success("🎉 DAILY GOALS COMPLETED! 🎉")
            if goal_service.log_daily_goals(st.session_state.user_id, german_hours, tech_hours, apps_sent, words_learned):
                goal_service.update_user_streak(st.session_state.user_id, streak_broken=False)

                # Check for achievements
                user = db_manager.get_user(st.session_state.user_id)
                if user:
                    streak = user['current_streak'] # current_streak is already updated by update_user_streak
                    if streak == 7:
                        if goal_service.add_achievement(st.session_state.user_id, "Week Warrior"):
                            st.balloons()
                            st.info("🏆 Achievement Unlocked: Week Warrior!")
                    elif streak == 30:
                        if goal_service.add_achievement(st.session_state.user_id, "Monthly Master"):
                            st.balloons()
                            st.info("🏆 Achievement Unlocked: Monthly Master!")
                    elif streak == 100:
                        if goal_service.add_achievement(st.session_state.user_id, "Century Champion"):
                            st.balloons()
                            st.info("🏆 Achievement Unlocked: Century Champion!")
                    elif streak == 365:
                        if goal_service.add_achievement(st.session_state.user_id, "Yearly Legend"):
                            st.balloons()
                            st.info("🏆 Achievement Unlocked: Yearly Legend!")

                if st.button("Back to Dashboard"):
                    st.session_state.page = 'dashboard'
                    st.rerun()
        else:
            st.error("❌ DAILY GOALS NOT MET! ❌")
            st.write("Minimum requirements:")
            st.write("- 2 hours German study")
            st.write("- 3 hours tech development")
            st.write("- 5 job applications")
            st.write("- 50 German words learned")

            # Break streak and lock app
            goal_service.update_user_streak(st.session_state.user_id, streak_broken=True)
            goal_service.add_penalty(st.session_state.user_id, 10.0, "Daily goals not met")

            st.warning("App locked for 24 hours! Complete redemption tasks to unlock.")

            if st.button("Go to Lock Screen"):
                st.session_state.page = 'lock'
                st.rerun()

def lock_page():
    """Displays the app lock screen and redemption options."""
    st.title("🔒 APP LOCKED!")

    user = db_manager.get_user(st.session_state.user_id)
    if not user:
        st.error("User not found.")
        return

    lock_end = user['lock_end_date'] # get 'lock_end_date' using dict key

    st.error(f"You missed your daily goals and the app is locked until {lock_end}")

    st.write("Complete redemption tasks to unlock early:")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📚 3h German Study"):
            # Log the redemption task as a daily goal for today
            if goal_service.log_daily_goals(st.session_state.user_id, german_hours=3.0, checkin_completed=1):
                if goal_service.unlock_app(st.session_state.user_id):
                    st.success("Redemption completed! App unlocked.")
                    st.session_state.page = 'dashboard'
                    st.rerun()
                else:
                    st.error("Failed to unlock app.")
            else:
                st.error("Failed to log redemption task.")

    with col2:
        if st.button("💼 10 Applications"):
            # Log the redemption task as a daily goal for today
            if goal_service.log_daily_goals(st.session_state.user_id, applications_sent=10, checkin_completed=1):
                if goal_service.unlock_app(st.session_state.user_id):
                    st.success("Redemption completed! App unlocked.")
                    st.session_state.page = 'dashboard'
                    st.rerun()
                else:
                    st.error("Failed to unlock app.")
            else:
                st.error("Failed to log redemption task.")

    with col3:
        if st.button("💰 Pay $20"):
            if goal_service.add_penalty(st.session_state.user_id, 20.0, "Redemption payment"):
                if goal_service.unlock_app(st.session_state.user_id):
                    st.success("Payment completed! App unlocked.")
                    st.session_state.page = 'dashboard'
                    st.rerun()
                else:
                    st.error("Failed to unlock app.")
            else:
                st.error("Failed to record payment.")


def german_practice_page():
    """Provides AI-powered German practice exercises."""
    st.title("🇩🇪 German Practice with AI")

    user = db_manager.get_user(st.session_state.user_id)
    if not user:
        return

    gemini_api_key = user['gemini_api_key']

    use_ai = False
    if not GEMINI_AVAILABLE:
        st.warning("Google Generative AI package not installed. Showing default exercises.")
    elif not gemini_api_key:
        st.warning("Please add your Gemini API key in Settings to use AI-powered features.")
        if st.button("Go to Settings"):
            st.session_state.page = 'settings'
            st.rerun()
    else:
        use_ai = True
        if not st.session_state.gemini_configured:
            with st.spinner("Configuring AI..."):
                if not ai_service.configure_gemini(gemini_api_key):
                    st.error("Could not configure Gemini. Using default exercises.")
                    use_ai = False
                else:
                    st.session_state.gemini_configured = True # Update session state

    st.write("Practice German with exercises tailored to your level!")

    # Get user level
    level = user['current_level']

    # Exercise focus options
    focus_options = ["vocabulary", "grammar", "conversation", "business German"]
    focus_area = st.selectbox("Choose focus area:", focus_options)

    # Level selector
    level_options = ["A1", "A2", "B1", "B2", "C1", "C2"]
    selected_level = st.selectbox("Practice level:", level_options, index=level_options.index(level) if level in level_options else 0)

    # Generate exercises
    if st.button("Generate New Exercises") or 'current_exercises' not in st.session_state:
        with st.spinner("Generating exercises..."):
            exercises = ai_service.generate_german_exercises(selected_level, gemini_api_key if use_ai else None, focus_area)
            st.session_state.current_exercises = exercises

    # Display exercises
    if 'current_exercises' in st.session_state:
        exercises = st.session_state.current_exercises

        st.subheader(f"German Exercises ({selected_level} Level - {focus_area.title()})")

        user_answers = {}
        for i, exercise in enumerate(exercises, 1):
            st.write(f"**Exercise {i}:**")
            st.write(exercise)

            answer_key = f"exercise_answer_{i}_{selected_level}_{focus_area}"
            answer = st.text_area(
                f"Your answer for exercise {i}:",
                key=answer_key,
                height=100,
                placeholder="Type your answer here..."
            )
            user_answers[i] = answer
            st.divider()

        # Submit answers
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Submit Answers"):
                completed_answers = sum(1 for answer in user_answers.values() if answer.strip())
                if completed_answers > 0:
                    st.success(f"Great job! You completed {completed_answers} out of {len(exercises)} exercises.")
                    estimated_words = completed_answers * 5 # Simple estimation
                    st.info(f"Estimated German words practiced: {estimated_words}")
                else:
                    st.warning("Please complete at least one exercise before submitting.")
        with col2:
            if st.button("🔄 New Exercises"):
                if 'current_exercises' in st.session_state:
                    del st.session_state.current_exercises
                st.rerun()
        with col3:
            if st.button("📚 Study Tips"):
                st.info("""
                **German Study Tips:**
                - Practice daily for consistency
                - Focus on practical vocabulary for work
                - Use German in real situations when possible
                - Watch German news/videos with subtitles
                - Join German language exchange groups
                """)

    if st.button("🏠 Back to Dashboard"):
        st.session_state.page = 'dashboard'
        st.rerun()


def progress_page():
    """Shows detailed progress, achievements, and penalties."""
    st.title("📈 Detailed Progress")

    user = db_manager.get_user(st.session_state.user_id)
    if not user:
        return

    # User stats
    st.subheader("👤 Your Stats")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current Streak", f"{user['current_streak']} days")
    with col2:
        st.metric("Total Streak", f"{user['total_streak']} days")
    with col3:
        st.metric("Level", user['current_level'])
    with col4:
        st.metric("Money at Risk", f"${user['money_at_risk']}")

    # Achievements
    st.subheader("🏆 Achievements")
    achievements = goal_service.get_user_achievements(st.session_state.user_id)

    if achievements:
        df_achievements = pd.DataFrame(achievements) # Already dicts, so directly convertible
        st.table(df_achievements)
    else:
        st.info("No achievements yet. Keep going!")

    # Penalties
    st.subheader("💰 Penalties")
    penalties = goal_service.get_user_penalties(st.session_state.user_id)

    if penalties:
        df_penalties = pd.DataFrame(penalties) # Already dicts, so directly convertible
        st.table(df_penalties)
        total_penalty = sum([p['amount'] for p in penalties])
        st.metric("Total Pending Penalties", f"${total_penalty}")
    else:
        st.info("No pending penalties. Great job!")

    # Activity history
    st.subheader("📅 Activity History")
    streak_data = db_manager.get_streak_data(st.session_state.user_id)

    if streak_data:
        df = pd.DataFrame(streak_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        st.dataframe(df)

        if len(df) > 1:
            st.subheader("📊 Progress Visualization")
            st.line_chart(df.set_index('date')['german_hours'])
            st.caption("German Study Hours Over Time")
    else:
        st.info("No activity data yet.")

    if st.button("Back to Dashboard"):
        st.session_state.page = 'dashboard'
        st.rerun()

def api_status_page():
    """Displays information and documentation for the Flask API."""
    st.title("🔌 API Status & Documentation")

    # Start API server if not running
    # This section demonstrates how you *could* start it, but for production,
    # the Flask API should be deployed and run separately from Streamlit.
    if not st.session_state.api_running:
        st.info("The API server is typically run as a separate process in production. "
                "For local development, you can start it here.")
        if st.button("🚀 Start API Server (Local)"):
            try:
                # Start the Flask app in a separate daemon thread
                # This makes it run in the background and terminate with the main app
                api_thread = threading.Thread(target=lambda: flask_api_app_module.api_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True)
                api_thread.start()
                st.session_state.api_running = True
                st.success("API Server started on http://localhost:5000 (check your console for Flask logs)")
            except Exception as e:
                st.error(f"Failed to start API server: {str(e)}")
    else:
        st.success("✅ API Server is running on http://localhost:5000")

    if st.session_state.api_running:
        if st.button("📊 Test API Connection"):
            try:
                # Test the API connection (e.g., to a non-authenticated endpoint or expect 401)
                response = flask_api_app_module.requests.get("http://localhost:5000/api/user/1", timeout=5)
                if response.status_code == 401:
                    st.info("API is responding (authentication required as expected for user endpoint)")
                elif response.status_code == 404:
                    st.info("API is responding (user not found as expected without session token)")
                else:
                    st.success(f"API is responding normally. Status code: {response.status_code}")
            except Exception as e:
                st.error(f"API connection failed: {str(e)}")

    # API Documentation - static content for display
    st.subheader("📚 API Documentation")

    api_docs = {
        "Authentication": {
            "POST /api/login": {
                "description": "Login and get session token",
                "body": {"email": "user@example.com", "password": "password"},
                "response": {"session_token": "abc123", "user_id": 1, "name": "John"}
            }
        },
        "User Data": {
            "GET /api/user/<int:user_id>": {
                "description": "Get user information",
                "headers": {"Authorization": "Bearer {session_token}"},
                "response": {"id": 1, "email": "user@example.com", "name": "John", "current_streak": 5}
            }
        },
        "Daily Check-in": {
            "POST /api/checkin": {
                "description": "Submit daily goals",
                "headers": {"Authorization": "Bearer {session_token}"},
                "body": {"german_hours": 2.5, "tech_hours": 4.0, "applications_sent": 6, "words_learned": 75},
                "response": {"success": True, "goals_met": True, "message": "Daily goals completed!"}
            }
        },
        "Progress": {
            "GET /api/progress/<int:user_id>": {
                "description": "Get user progress data",
                "headers": {"Authorization": "Bearer {session_token}"},
                "response": {"streak_data": [], "achievements": [], "penalties": []}
            }
        }
    }

    for category, endpoints in api_docs.items():
        st.subheader(f"📋 {category}")
        for endpoint, details in endpoints.items():
            with st.expander(f"{endpoint}"):
                st.write(f"**Description:** {details['description']}")
                if 'headers' in details:
                    st.code(f"Headers:\n{json.dumps(details['headers'], indent=2)}")
                if 'body' in details:
                    st.code(f"Request Body:\n{json.dumps(details['body'], indent=2)}")
                st.code(f"Response:\n{json.dumps(details['response'], indent=2)}")

    # Example API usage
    st.subheader("💻 Example Usage (Python)")
    example_code = """
import requests

# Assuming your Flask API is running on http://localhost:5000

# Login
login_response = requests.post('http://localhost:5000/api/login', json={
    'email': 'your.email@example.com',
    'password': 'your_password'
})

if login_response.status_code == 200:
    data = login_response.json()
    session_token = data['session_token']
    user_id = data['user_id']

    # Get user info
    headers = {'Authorization': f'Bearer {session_token}'}
    user_response = requests.get(f'http://localhost:5000/api/user/{user_id}', headers=headers)
    print(f"User Info: {user_response.json()}")

    # Submit daily checkin
    checkin_response = requests.post('http://localhost:5000/api/checkin',
        headers=headers,
        json={
            'german_hours': 2.5,
            'tech_hours': 4.0,
            'applications_sent': 6,
            'words_learned': 75
        }
    )
    print(f"Check-in Response: {checkin_response.json()}")
else:
    print(f"Login failed: {login_response.status_code} - {login_response.text}")
"""
    st.code(example_code, language='python')


def settings_page():
    """Allows users to update their Gemini API key and perform emergency unlock."""
    st.title("⚙️ Settings")

    user = db_manager.get_user(st.session_state.user_id)
    if not user:
        return

    st.subheader("User Information")
    st.write(f"Email: {user['email']}")
    st.write(f"Name: {user['name']}")
    st.write(f"Start Date: {user['start_date']}")
    st.write(f"Money at Risk: ${user['money_at_risk']}")
    st.write(f"Last Login: {user['last_login'] if user['last_login'] else 'Never'}")

    if GEMINI_AVAILABLE:
        st.subheader("Gemini API Key")
        current_key_status = "set" if user['gemini_api_key'] else "not set"
        st.info(f"Your Gemini API key is currently: **{current_key_status}**")
        new_api_key = st.text_input("Update Gemini API Key", value="***hidden***" if user['gemini_api_key'] else "", type="password")

        if st.button("Update API Key"):
            if new_api_key and new_api_key != "***hidden***":
                if db_manager.update_gemini_api_key(st.session_state.user_id, new_api_key):
                    if ai_service.configure_gemini(new_api_key): # Re-configure Gemini instantly
                        st.session_state.gemini_configured = True
                        st.success("Gemini API key updated and configured successfully!")
                    else:
                        st.session_state.gemini_configured = False # Ensure state is false if config fails
                        st.warning("API key saved but could not be configured. Check the key.")
                else:
                    st.error("Failed to update API key in database.")
            elif not new_api_key: # User cleared the input
                if db_manager.update_gemini_api_key(st.session_state.user_id, None):
                    st.session_state.gemini_configured = False
                    st.info("API key cleared.")
                else:
                    st.error("Failed to clear API key in database.")
            else:
                st.info("No change detected in API key.")
    else:
        st.info("Install google-generativeai package to enable AI features")

    st.subheader("Emergency Options")

    # Emergency Unlock functionality
    # Note: This is an example of a destructive action, real apps would have more robust confirmations.
    if st.button("🚨 Emergency Unlock ($50)"):
        st.warning("🚨 EMERGENCY UNLOCK ACTIVATED 🚨")
        st.write("This will cost you $50 and reset your current streak!")

        if st.button("Confirm Emergency Unlock"):
            if goal_service.add_penalty(st.session_state.user_id, 50.0, "Emergency unlock"):
                if goal_service.reset_streak_and_unlock(st.session_state.user_id):
                    st.success("Emergency unlock complete. Streak reset. Keep going!")
                    st.session_state.page = 'dashboard'
                    st.rerun()
                else:
                    st.error("Error resetting streak and unlocking app.")
            else:
                st.error("Error recording emergency unlock penalty.")


    if st.button("Back to Dashboard"):
        st.session_state.page = 'dashboard'
        st.rerun()


# --- Main App Execution ---

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(
        page_title="Munich Path",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize database if not already done
    if not st.session_state.db_initialized:
        if not db_manager.init_database():
            st.error("Failed to initialize database. Please check file permissions or restart.")
            return

    # Sidebar navigation
    with st.sidebar:
        st.title("🚀 Munich Path")

        if st.session_state.user_id:
            user = db_manager.get_user(st.session_state.user_id)
            if user:
                st.write(f"Welcome, {user['name']}!")
                st.write(f"🔥 Streak: {user['current_streak']} days")
                st.write(f"📧 {user['email']}")

        # Navigation buttons based on login status
        if st.session_state.user_id:
            if st.button("🏠 Dashboard"):
                st.session_state.page = 'dashboard'
                st.rerun()
            if st.button("✅ Daily Check-in"):
                st.session_state.page = 'checkin'
                st.rerun()
            if st.button("🇩🇪 German Practice"):
                st.session_state.page = 'german_practice'
                st.rerun()
            if st.button("📈 Progress"):
                st.session_state.page = 'progress'
                st.rerun()
            if st.button("🔌 API Status"):
                st.session_state.page = 'api_status'
                st.rerun()
            if st.button("⚙️ Settings"):
                st.session_state.page = 'settings'
                st.rerun()

        # Logout button
        if st.button("🚪 Logout"):
            st.session_state.user_id = None
            st.session_state.page = 'login'
            st.session_state.gemini_configured = False # Reset Gemini config on logout
            st.rerun()

    # Page routing based on session state
    try:
        if st.session_state.user_id is None:
            login_page()
        else:
            if st.session_state.page == 'dashboard':
                dashboard_page()
            elif st.session_state.page == 'checkin':
                checkin_page()
            elif st.session_state.page == 'lock':
                lock_page()
            elif st.session_state.page == 'german_practice':
                german_practice_page()
            elif st.session_state.page == 'progress':
                progress_page()
            elif st.session_state.page == 'api_status':
                api_status_page()
            elif st.session_state.page == 'settings':
                settings_page()
            else: # Fallback for unknown pages
                st.session_state.page = 'dashboard'
                st.rerun()
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        st.error("Please refresh the page or restart the app if the issue persists.")
        # Optionally, provide a way to go back to login or dashboard
        if st.button("Go to Login"):
            st.session_state.user_id = None
            st.session_state.page = 'login'
            st.rerun()


if __name__ == "__main__":
    main()
