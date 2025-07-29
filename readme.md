# 🚀 Munich Path: A Strategic Application for Professional Development and Cultural Integration

This project, **Munich Path**, represents a comprehensive full-stack application developed to facilitate systematic preparation for relocation to Germany and, specifically, to enhance candidacy for the "Make it in Munich" program by the conclusion of the current year.

Like many aspiring professionals, I wanted to join the "Make it in Munich" program but struggled with consistency in learning and preparation. This app was born from that personal challenge. It serves as a digital accountability partner — ensuring I stay on track, practice consistently, and build the discipline needed to achieve this life-changing goal.

It is designed as a robust tool for personal accountability to foster consistent habits and provide a structured approach to:

- 🇩🇪 German language acquisition
- 💻 Technical skill refinement
- 🏛️ Job market navigation

It serves a dual purpose:

1. To systematically advance German language proficiency
2. To construct a practical portfolio that reflects dedication and technical acumen

Ultimately, it functions as a **digital companion** for individuals committed to achieving their aspirations of establishing a new life in Germany.

---

## ✨ Core Functionalities

- **Secure User Management**: Registration, authentication, and password recovery with email verification.
- **Daily Objective Tracking**: Monitor German study, tech upskilling, job applications, and vocabulary.
- **Streak Maintenance System**: Motivates consistency through streak rewards.
- **Achievement & Gamification**: Earn badges and level-ups for sustained effort.
- **Accountability & Penalties**: Financial commitment and lockouts for non-compliance.
- **AI-Powered Practice**: Gemini API integration for German exercises (optional).
- **Progress Visualization**: Detailed insights into streaks, achievements, and penalties.
- **RESTful API**: Flask-based backend powering the logic and data handling.

---

## 🛠️ Technological Stack

| Layer    | Technology               |
| -------- | ------------------------ |
| Frontend | Streamlit                |
| Backend  | Flask (REST API)         |
| Database | SQLite3                  |
| AI       | Google Gemini API        |
| Auth     | Custom hashed auth/email |
| Email    | SMTP via smtplib         |
| Data     | Pandas                   |

---

## 📆 Project Directory Structure

```
munich_path/
├── .gitignore
├── README.md
├── requirements.txt
├── app.py                  # Streamlit entry point
├── config.py               # Config (email + Gemini keys)
├── database/
│   ├── __init__.py
│   └── db_manager.py
├── services/
│   ├── __init__.py
│   ├── auth_service.py
│   ├── goal_service.py
│   └── ai_service.py
├── api/
│   ├── __init__.py
│   ├── api.py
│   └── routes.py
├── utils/
│   ├── __init__.py
│   └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── test_auth_service.py
│   ├── test_goal_service.py
│   └── test_api_routes.py
```

---

## 🚀 Installation and Execution Guide

### Prerequisites

- Python 3.8+
- pip

### 1. Clone Repository

```bash
git clone https://github.com/your-username/munich_path.git
cd munich_path
```

### 2. Setup Virtual Environment

```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install Requirements

```bash
pip install -r requirements.txt
```

### 4. Create Environment Variables

Create a `.env` file:

```env
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_ADDRESS=your.email@gmail.com
EMAIL_PASSWORD=your_generated_app_password
GEMINI_API_KEY=your_gemini_api_key
```

### 5. Run the App

```bash
streamlit run app.py
```

---

## 🌐 API Reference

Base URL: `http://localhost:5000`

### Auth Endpoints

**POST /api/login**

```json
{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response:**

```json
{
  "success": true,
  "session_token": "token_string",
  "user_id": 123,
  "name": "John Doe"
}
```

### User Info

**GET /api/user/\<user\_id>**

Header:

```http
Authorization: Bearer <session_token>
```

### Check-in

**POST /api/checkin**

```json
{
  "german_hours": 2.5,
  "tech_hours": 4.0,
  "applications_sent": 6,
  "words_learned": 75
}
```

### Progress

**GET /api/progress/\<user\_id>**

```json
{
  "streak_data": [...],
  "achievements": [...],
  "penalties": [...]
}
```

---

## 🧪 Testing

```bash
python -m unittest discover munich_path/tests
```

---

## 🤝 Contributing

All contributions welcome! Submit issues, PRs, or feature suggestions.

---

## 📞 Contact

For inquiries or collaboration: [Your Name] • [[your.email@example.com](mailto\:your.email@example.com)] • [GitHub Profile URL]

# munich-path
