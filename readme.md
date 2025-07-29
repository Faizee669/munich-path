# 🚀 Munich Path: A Strategic Application for Professional Development and Cultural Integration

This project, **Munich Path**, represents a comprehensive full-stack application developed to facilitate systematic preparation for relocation to Germany, specifically to enhance candidacy for the "Make it in Munich" program by the conclusion of the current year. I wanted to relocate to Germany with the Make it in Munich program but didn’t have a sufficient portfolio and lacked proficiency in the German language, so I created this application to track my progress and stay committed. The process of international relocation, particularly to a country with a distinct language and cultural framework, presents significant challenges. This application was conceived as a robust tool for personal accountability, designed to foster consistent habits and provide a structured approach to German language acquisition, technical skill refinement, and job market navigation. It serves a dual purpose: to systematically advance German language proficiency and to construct a substantial, practical portfolio that underscores both dedication and technical acumen, directly supporting my objectives for the aforementioned program. Ultimately, it functions as a digital companion for individuals committed to achieving their aspirations of establishing a new life in Germany.

## ✨ Core Functionalities

- **Secure User Management**: Implements robust user registration, authentication, and password recovery mechanisms, including email verification, to ensure a secure and personalized environment for progress tracking.
- **Daily Objective Tracking**: Provides capabilities for users to define and monitor daily commitments across critical areas such as German language study, technical skill development, job application submissions, and vocabulary expansion.
- **Streak Maintenance System**: Incorporates a motivational streak system that recognizes and rewards consistent daily engagement, thereby encouraging persistent effort.
- **Achievement and Gamification Integration**: Features a system for unlocking achievements based on milestones and sustained streaks, transforming the preparatory journey into a series of attainable goals.
- **Accountability and Penalty Framework**: Establishes a system involving financial commitment and temporary application lockouts for non-compliance with daily objectives, designed to reinforce self-discipline.
- **AI-Enhanced German Language Practice (Optional)**: Integrates with the Google Gemini API to generate tailored German language exercises. This feature is instrumental for targeted practice, particularly for achieving the linguistic proficiency required by programs such as "Make it in Munich."
- **Comprehensive Progress Visualization**: Offers detailed insights into user activity history, earned achievements, and pending penalties, providing a clear overview of progress and areas requiring further attention.
- **Internal RESTful API Architecture**: Utilizes a Flask-based RESTful API as the backend, responsible for data persistence and the execution of business logic. This modular design exemplifies scalable architectural principles, serving as a significant component of the development portfolio.

## 🛠️ Technological Stack

- **Frontend**: Streamlit for efficient application development and the creation of an interactive, user-centric interface.
- **Backend**: Flask for constructing a lightweight yet powerful RESTful API to manage core application logic.
- **Database**: SQLite3 for local data storage and streamlined data management.
- **Authentication**: Custom implementations for password hashing, secure token generation, and reliable email-based password reset protocols.
- **Artificial Intelligence Integration**: Google Gemini API for intelligent content generation, specifically for German language practice.
- **Email Services**: smtplib for the secure handling of password reset email communications.
- **Data Analysis**: Pandas for effective data manipulation and clear presentation of user progress.

## 📦 Project Directory Structure

```
munich_path/
├── .gitignore
├── README.md
├── requirements.txt
├── app.py                  # Primary entry point for the Streamlit application
├── config.py               # Centralized configuration settings (e.g., email, AI keys via environment variables)
├── database/
│   ├── __init__.py         # Designates as a Python package
│   └── db_manager.py       # Manages all SQLite database interactions
├── services/
│   ├── __init__.py         # Designates as a Python package
│   ├── auth_service.py     # Encapsulates user authentication, registration, and password reset logic
│   ├── goal_service.py     # Contains logic for daily goals, streaks, penalties, and achievements
│   └── ai_service.py       # Manages Gemini AI integration and exercise generation
├── api/
│   ├── __init__.py         # Designates as a Python package
│   ├── api.py              # Flask application instance and server initiation
│   └── routes.py           # Defines all Flask API endpoints
├── utils/
│   ├── __init__.py         # Designates as a Python package
│   └── helpers.py          # General utility functions (e.g., password hashing, email validation)
├── tests/                  # Automated tests for services and API functionalities
│   ├── __init__.py         # Designates as a Python package
│   ├── test_auth_service.py
│   ├── test_goal_service.py
│   └── test_api_routes.py
```

## 🚀 Installation and Operation Guide

The following steps outline the procedure for setting up and executing the **Munich Path** application locally.

### Prerequisites

- Python 3.8+
- pip (Python package installer)

### 1. Repository Cloning

```bash
git clone https://github.com/your-username/munich_path.git
cd munich_path
```

### 2. Virtual Environment Setup (Recommended Practice)

```bash
python -m venv venv
# For Windows environments
.\venv\Scripts\activate
# For macOS/Linux environments
source venv/bin/activate
```

### 3. Dependency Installation

```bash
pip install -r requirements.txt
```

### 4. Environment Variable Configuration

Create a `.env` file within the `munich_path/` root directory (co-located with `app.py`) to store sensitive configurations. It is imperative that this file is excluded from version control (e.g., via `.gitignore`).

```plaintext
# Email Configuration for Password Reset (e.g., Gmail SMTP settings)
# Note: Gmail users with 2-Factor Authentication may need to generate an "App Password."
# Refer to Google's support documentation for details: https://support.google.com/accounts/answer/185833
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_ADDRESS=your.email@gmail.com
EMAIL_PASSWORD=your_generated_app_password

# Optional: Google Gemini API Key for AI-powered features
# Obtain an API key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key
```

### 5. Application Execution

From the `munich_path` directory (the project root), initiate the Streamlit application:

```bash
streamlit run app.py
```

This command will launch the Streamlit application in your default web browser.

### 6. Flask API Server Initialization (for Local Interaction)

The Flask API operates in a separate thread. For local testing and demonstration purposes, the API server can be activated from the "API Status" page within the Streamlit user interface.

For production deployments, the Flask API should typically be run as an independent service utilizing a WSGI server such as Gunicorn.

## 🌐 API Reference

The **Munich Path** application incorporates a RESTful API that manages all backend operations. This API can be accessed directly or via the Streamlit frontend.

**Local Base URL**: `http://localhost:5000`

### Authentication Endpoints

#### POST /api/login

**Description**: Authenticates a user and issues a session token.

**Request Body (JSON)**:

```json
{
    "email": "user@example.com",
    "password": "your_password"
}
```

**Successful Response (HTTP 200 OK)**:

```json
{
    "success": true,
    "session_token": "a_long_generated_token_string",
    "user_id": 123,
    "name": "John Doe"
}
```

**Error Responses (HTTP 400 Bad Request / HTTP 401 Unauthorized)**:

```json
{
    "success": false,
    "error": "Email and password required"
}
```

or

```json
{
    "success": false,
    "error": "Invalid credentials"
}
```

### User Data Endpoints

#### GET /api/user/<int:user_id>

**Description**: Retrieves essential information for a specified user.

**Request Headers**:

```
Authorization: Bearer <session_token>
```

**Successful Response (HTTP 200 OK)**:

```json
{
    "id": 123,
    "email": "user@example.com",
    "name": "John Doe",
    "current_streak": 5,
    "total_streak": 15,
    "level": "Achiever",
    "money_at_risk": 100.0
}
```

**Error Responses (HTTP 401 Unauthorized / HTTP 404 Not Found)**:

```json
{
    "success": false,
    "error": "Invalid session"
}
```

### Daily Check-in Endpoints

#### POST /api/checkin

**Description**: Submits a user's daily goal achievements and updates their streak status.

**Request Headers**:

```
Authorization: Bearer <session_token>
```

**Request Body (JSON)**:

```json
{
    "german_hours": 2.5,
    "tech_hours": 4.0,
    "applications_sent": 6,
    "words_learned": 75
}
```

**Successful Response (HTTP 200 OK)**:

```json
{
    "success": true,
    "goals_met": true,
    "message": "Daily goals completed!"
}
```

*(In instances where goals are not met, the `goals_met` field will be `false`, and the `message` will indicate application lockout.)*

### Progress Data Endpoints

#### GET /api/progress/<int:user_id>

**Description**: Retrieves all progress-related data for a user, including streak history, achievements, and accrued penalties.

**Request Headers**:

```
Authorization: Bearer <session_token>
```

**Successful Response (HTTP 200 OK)**:

```json
{
    "streak_data": [
        {"date": "2023-01-01", "german_hours": 2.0, "tech_hours": 3.0, "applications_sent": 5},
        {"date": "2023-01-02", "german_hours": 2.5, "tech_hours": 4.0, "applications_sent": 7}
    ],
    "achievements": [
        {"achievement_name": "Week Warrior", "date_earned": "2023-01-07"}
    ],
    "penalties": [
        {"amount": 10.0, "reason": "Daily goals not met", "date": "2023-01-03"}
    ]
}
```

**Error Responses (HTTP 401 Unauthorized / HTTP 404 Not Found)**:

```json
{
    "success": false,
    "error": "Invalid session"
}
```

## 🧪 Automated Testing

To execute the automated tests for this project, navigate to the `munich_path` directory (the project root) and invoke the following command:

```bash
python -m unittest discover munich_path/tests
```

This command will discover and execute all test cases located within the `tests/` directory.

## 🤝 Contribution Guidelines

Contributions are welcomed. Please feel encouraged to submit issues, propose pull requests, or offer suggestions for improvement.
