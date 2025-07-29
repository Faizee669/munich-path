import os

# --- Email Configuration ---
# IMPORTANT: For production, store these in environment variables (e.g., in a .env file)
# Example:
# EMAIL_SMTP_SERVER="smtp.gmail.com"
# EMAIL_SMTP_PORT=587
# EMAIL_ADDRESS="your-email@gmail.com"
# EMAIL_PASSWORD="your-app-password" (use an app password for Gmail)

EMAIL_CONFIG = {
    'smtp_server': os.environ.get('EMAIL_SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.environ.get('EMAIL_SMTP_PORT', 587)),
    'email': os.environ.get('EMAIL_ADDRESS', 'your-email@gmail.com'), # Replace with your email or set as env var
    'password': os.environ.get('EMAIL_PASSWORD', 'your-app-password')   # Replace with your app password or set as env var
}

# --- Gemini API Availability ---
# This checks if the google-generativeai package is installed.
# It allows the app to run even without AI features if the package isn't present.
try:
    import google.generativeai as genai # This import is for checking availability only
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# --- Database Configuration ---
# Define the path for the SQLite database
DATABASE_NAME = 'munich_path.db'

# You can add other configurations here as your project grows, e.g.:
# DEFAULT_MONEY_AT_RISK = 100.0
# DEFAULT_GERMAN_GOAL_HOURS = 2.0
# DEFAULT_TECH_GOAL_HOURS = 3.0
# DEFAULT_APPS_SENT_GOAL = 5
# DEFAULT_WORDS_LEARNED_GOAL = 50
