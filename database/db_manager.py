import sqlite3
from datetime import datetime, timedelta
from munich_path.config import DATABASE_NAME # Import database name from config

def get_db_connection():
    """Establishes and returns a database connection."""
    conn = sqlite3.connect(DATABASE_NAME)
    # Set row_factory to sqlite3.Row to allow accessing columns by name
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initializes the database by creating necessary tables if they don't exist."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Users table (updated with all fields)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                current_level TEXT DEFAULT 'Dreamer',
                total_streak INTEGER DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                last_checkin TEXT,
                money_at_risk REAL DEFAULT 0.0,
                is_locked INTEGER DEFAULT 0,
                lock_end_date TEXT,
                gemini_api_key TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT,
                email_verified INTEGER DEFAULT 0,
                reset_token TEXT,
                reset_token_expires TEXT
            )
        ''')

        # Daily goals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_goals (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                date TEXT NOT NULL,
                german_hours REAL DEFAULT 0.0,
                tech_hours REAL DEFAULT 0.0,
                applications_sent INTEGER DEFAULT 0,
                words_learned INTEGER DEFAULT 0,
                checkin_completed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Achievements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                achievement_name TEXT NOT NULL,
                date_earned TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Penalties table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS penalties (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                amount REAL NOT NULL,
                reason TEXT NOT NULL,
                date TEXT NOT NULL,
                paid INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # API sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                session_token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Database initialization failed: {e}") # Print to console for debugging
        return False

# --- User Management ---

def create_user_db(email, password_hash, name, start_date, money_at_risk, gemini_api_key):
    """Inserts a new user into the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (email, password_hash, name, start_date, money_at_risk, gemini_api_key)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (email, password_hash, name, start_date.strftime('%Y-%m-%d'), money_at_risk, gemini_api_key))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        # This catches UNIQUE constraint failed errors (e.g., duplicate email)
        conn.close()
        return None # Indicate user creation failed due to duplicate email
    except sqlite3.Error as e:
        print(f"Error creating user in DB: {e}")
        conn.close()
        return None

def get_user(user_id):
    """Fetches a user's data by their ID, returning it as a dictionary."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        return dict(user_data) if user_data else None
    except sqlite3.Error as e:
        print(f"Error getting user from DB: {e}")
        return None

def get_user_by_email(email):
    """Fetches a user's data by their email, returning it as a dictionary."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user_data = cursor.fetchone()
        conn.close()
        return dict(user_data) if user_data else None
    except sqlite3.Error as e:
        print(f"Error getting user by email from DB: {e}")
        return None

def update_user_login_time(user_id):
    """Updates the last_login timestamp for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?',
                     (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error updating last login time: {e}")
        return False

def update_gemini_api_key(user_id, api_key):
    """Updates the Gemini API key for a specific user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET gemini_api_key = ? WHERE id = ?', (api_key, user_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error updating API key in DB: {e}")
        return False

def update_user_password(email, new_password_hash):
    """Updates a user's password."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET password_hash = ?
            WHERE email = ?
        ''', (new_password_hash, email))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error updating password in DB: {e}")
        return False

# --- Password Reset Token Management ---

def store_reset_token(email, reset_token, expires_at):
    """Stores a password reset token for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET reset_token = ?, reset_token_expires = ?
            WHERE email = ?
        ''', (reset_token, expires_at.strftime('%Y-%m-%d %H:%M:%S'), email))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error storing reset token in DB: {e}")
        return False

def get_reset_token_info(email, reset_token):
    """Retrieves reset token information for validation."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, reset_token_expires FROM users
            WHERE email = ? AND reset_token = ?
        ''', (email, reset_token))
        token_info = cursor.fetchone()
        conn.close()
        return dict(token_info) if token_info else None
    except sqlite3.Error as e:
        print(f"Error getting reset token info from DB: {e}")
        return None

def clear_reset_token(email):
    """Clears the reset token for a user after it's been used or expired."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET reset_token = NULL, reset_token_expires = NULL
            WHERE email = ?
        ''', (email,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error clearing reset token in DB: {e}")
        return False

# --- Daily Goals & Streak Management ---

def log_daily_goals_db(user_id, date, german_hours, tech_hours, applications_sent, words_learned, checkin_completed):
    """Inserts or updates daily goals for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM daily_goals
            WHERE user_id = ? AND date = ?
        ''', (user_id, date.strftime('%Y-%m-%d')))
        
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE daily_goals
                SET german_hours = ?, tech_hours = ?, applications_sent = ?,
                    words_learned = ?, checkin_completed = ?
                WHERE user_id = ? AND date = ?
            ''', (german_hours, tech_hours, applications_sent,
                  words_learned, checkin_completed, user_id, date.strftime('%Y-%m-%d')))
        else:
            cursor.execute('''
                INSERT INTO daily_goals
                (user_id, date, german_hours, tech_hours, applications_sent, words_learned, checkin_completed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, date.strftime('%Y-%m-%d'), german_hours, tech_hours,
                  applications_sent, words_learned, checkin_completed))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error logging daily goals in DB: {e}")
        return False

def get_daily_goal_completion_status(user_id, date):
    """Checks if a user has completed their daily check-in for a given date."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT checkin_completed FROM daily_goals
            WHERE user_id = ? AND date = ?
        ''', (user_id, date.strftime('%Y-%m-%d')))
        result = cursor.fetchone()
        conn.close()
        return result['checkin_completed'] == 1 if result else False
    except sqlite3.Error as e:
        print(f"Error checking daily completion status: {e}")
        return False

def update_user_streak_data(user_id, current_streak, total_streak, is_locked, lock_end_date, last_checkin):
    """Updates user streak and lock status."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET current_streak = ?,
                total_streak = ?,
                is_locked = ?,
                lock_end_date = ?,
                last_checkin = ?
            WHERE id = ?
        ''', (current_streak, total_streak, is_locked,
              lock_end_date.strftime('%Y-%m-%d') if lock_end_date else None,
              last_checkin.strftime('%Y-%m-%d') if last_checkin else None,
              user_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error updating streak data: {e}")
        return False

def unlock_app_db(user_id):
    """Unlocks the app for a user by resetting lock status."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_locked = 0, lock_end_date = NULL WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error unlocking app in DB: {e}")
        return False

def reset_streak_and_unlock_db(user_id):
    """Resets the current streak and unlocks the app (for emergency unlock)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET current_streak = 0, is_locked = 0, lock_end_date = NULL
            WHERE id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error resetting streak and unlocking app in DB: {e}")
        return False

# --- Achievements ---

def add_achievement_db(user_id, achievement_name, date_earned):
    """Adds a new achievement for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO achievements (user_id, achievement_name, date_earned)
            VALUES (?, ?, ?)
        ''', (user_id, achievement_name, date_earned.strftime('%Y-%m-%d')))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Achievement already exists for this user, do nothing or log
        conn.close()
        return False
    except sqlite3.Error as e:
        print(f"Error adding achievement in DB: {e}")
        return False

def get_user_achievements(user_id):
    """Fetches all achievements for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT achievement_name, date_earned FROM achievements
            WHERE user_id = ? ORDER BY date_earned DESC
        ''', (user_id,))
        achievements = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return achievements
    except sqlite3.Error as e:
        print(f"Error getting achievements from DB: {e}")
        return []

# --- Penalties ---

def add_penalty_db(user_id, amount, reason, date):
    """Adds a new penalty for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO penalties (user_id, amount, reason, date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, reason, date.strftime('%Y-%m-%d')))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error adding penalty in DB: {e}")
        return False

def get_user_penalties(user_id):
    """Fetches all unpaid penalties for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT amount, reason, date FROM penalties
            WHERE user_id = ? AND paid = 0
            ORDER BY date DESC
        ''', (user_id,))
        penalties = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return penalties
    except sqlite3.Error as e:
        print(f"Error getting penalties from DB: {e}")
        return []

# --- Progress Data ---

def get_streak_data(user_id):
    """Fetches daily goal data for charting progress."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date, german_hours, tech_hours, applications_sent, words_learned, checkin_completed
            FROM daily_goals
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT 30
        ''', (user_id,))
        data = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return data
    except sqlite3.Error as e:
        print(f"Error getting streak data from DB: {e}")
        return []

# --- API Session Management ---

def create_api_session_db(user_id, session_token, expires_at):
    """Creates a new API session entry in the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO api_sessions (user_id, session_token, expires_at)
            VALUES (?, ?, ?)
        ''', (user_id, session_token, expires_at.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error creating API session in DB: {e}")
        return False

def validate_api_session_db(session_token):
    """Validates an API session token and returns the user ID if valid."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id FROM api_sessions
            WHERE session_token = ? AND expires_at > ?
        ''', (session_token, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        result = cursor.fetchone()
        conn.close()
        return result['user_id'] if result else None
    except sqlite3.Error as e:
        print(f"Error validating API session in DB: {e}")
        return None

