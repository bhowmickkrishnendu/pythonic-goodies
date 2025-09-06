# 🐦 Twitter Scheduler API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Flask](https://img.shields.io/badge/flask-2.x-green)
![MySQL](https://img.shields.io/badge/mysql-8.x-orange)
![Docker](https://img.shields.io/badge/docker-ready-blue)

A secure **Flask-based REST API** for scheduling, posting, and managing Twitter threads, with advanced **user authentication**, **admin controls**, and **job management**.  
Built for **multi-user environments** with support for **2FA, JWT, MySQL persistence**, and robust **admin features**.

---

## ✨ Features

### 🔐 User Authentication
- JWT-based login/logout  
- Google reCAPTCHA integration  
- Two-Factor Authentication (2FA) via TOTP (QR code provisioning)  
- Account lockout after repeated failed logins  
- Login attempt logging and history  

### 🛠️ Admin Controls
- Promote/demote users to admin  
- Unlock locked accounts  
- Delete users and clean up their scheduled jobs  
- View all users and their scheduled posts  
- Clean up orphaned jobs (for deleted users)  
- Dashboard with user, login, and scheduled post statistics  
- System info endpoint  

### 🐦 Twitter Scheduling
- Schedule single or multi-part (threaded) posts  
- Posts are split into 280-character chunks and posted as threads  
- View, cancel, and manage scheduled posts  
- Persistent job storage using **MySQL** and **APScheduler**  

### 🔒 Security
- JWT token blacklist for logout  
- Password hashing (Werkzeug)  
- CORS support for frontend integration  

---

## 🛠️ Tech Stack
- **Python (Flask)**  
- **MySQL** (persistent storage)  
- **APScheduler** (job scheduling)  
- **Tweepy** (Twitter API)  
- **SQLAlchemy** (ORM)  
- **flask-jwt-extended** (JWT auth)  
- **pyotp**, **qrcode** (2FA)  
- **Google reCAPTCHA**  
- **Docker-compatible**  

---

## 🚀 Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/bhowmickkrishnendu/pythonic-goodies.git
cd twitter-scheduler-api
```

### 2️⃣ Install Dependencies
Create a virtual environment (recommended) and install packages:
```bash
python -m venv venv
source venv/bin/activate   # On Linux/Mac
venv\Scripts\activate      # On Windows
pip install -r requirements.txt
```

### 3️⃣ Configure MySQL
- Create a MySQL database named **apscheduler_db**.  
- Ensure your MySQL server is running and accessible.  

### 4️⃣ Prepare `keys.txt`
Create a file named `keys.txt` in the project root with the following lines (one per line):  
```
TWITTER_API_KEY
TWITTER_API_SECRET
TWITTER_ACCESS_TOKEN
TWITTER_ACCESS_SECRET
RECAPTCHA_SECRET_KEY
JWT_SECRET_KEY
```
Replace each line with your actual credentials.

### 5️⃣ Run the API
```bash
flask run
```
The API will start at: **http://localhost:5000**

---

## 📡 API Endpoints

### 🔐 Authentication
- `POST /auth/login` — Login with username, password, reCAPTCHA, and optional 2FA  
- `POST /auth/logout` — Logout (JWT blacklist)  
- `POST /auth/setup-2fa` — Initiate 2FA setup (returns QR code)  
- `POST /auth/confirm-2fa` — Confirm and enable 2FA  
- `POST /auth/disable-2fa` — Disable 2FA  
- `GET /auth/profile` — Get user profile and login history  
- `POST /auth/unlock-account` — Admin unlocks a user account  

### 🛠️ Admin
- `POST /admin/set-admin-status` — Promote/demote user to admin  
- `GET /admin/users` — List all users  
- `DELETE /admin/delete-user-with-cleanup` — Delete user and their jobs  
- `POST /admin/cleanup-orphaned-jobs` — Remove jobs for deleted users  
- `GET /admin/dashboard` — View admin dashboard stats  
- `GET /admin/system-info` — System info  

### 🐦 Twitter Scheduling
- `POST /schedule_posts` — Schedule one or more posts (threaded if >280 chars)  
- `GET /scheduled_posts` — List scheduled posts (admin sees all)  
- `DELETE /cancel_post/<job_id>` — Cancel a scheduled post (user or admin)  
- `DELETE /admin/cancel_post/<job_id>` — Admin cancels any post  

### 📋 Misc
- `GET /health` — Health check  

---

## 📌 Notes
- All sensitive endpoints require **JWT authentication**.  
- Admin-only endpoints require the user to be an **admin**.  
- Scheduled posts are stored in MySQL and managed by APScheduler.  
- 2FA uses **TOTP** (compatible with Google Authenticator, Authy, etc.).  
- CORS is enabled for **http://localhost:3000** (customize as needed).  

---

## 📜 License
This project is licensed under the **MIT License**.
