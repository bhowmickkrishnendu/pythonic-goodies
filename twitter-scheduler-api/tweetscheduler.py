from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity, get_jwt
import tweepy
import time
from sqlalchemy import create_engine
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta
import mysql.connector
from werkzeug.security import check_password_hash
import requests
import pyotp
import qrcode
import io
import base64
from functools import wraps
import secrets

app = Flask(__name__)


# JWT Configuration
app.config['JWT_SECRET_KEY'] = secrets.token_hex(32)  # Change this to a random secret key
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
jwt = JWTManager(app)

# Read API keys and MySQL credentials from keys.txt
def read_keys(filename="keys.txt"):
    with open(filename, "r") as f:
        keys = f.read().strip().split('\n')
    # Now expecting 7 lines: existing 6 + RECAPTCHA_SECRET
    if len(keys) != 7:
        raise ValueError("keys.txt must contain exactly 7 lines: API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET, MYSQL_USER, MYSQL_PASS, RECAPTCHA_SECRET")
    return keys

consumer_key, consumer_secret, access_token, access_token_secret, mysql_user, mysql_password, recaptcha_secret = read_keys()

# MySQL configuration
MYSQL_HOST = 'localhost'
MYSQL_DB = 'apscheduler_db'

# Database connection
def get_db_connection():
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=mysql_user,
        password=mysql_password,
        database=MYSQL_DB
    )
    cursor = conn.cursor()
    cursor.execute("SET time_zone = '+05:30'")
    cursor.close()
    return conn

# Initialize database tables
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table with is_admin column
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            totp_secret VARCHAR(32),
            is_2fa_enabled BOOLEAN DEFAULT FALSE,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP NULL,
            last_login_ip VARCHAR(45) NULL,
            last_failed_login_at TIMESTAMP NULL,
            last_failed_login_ip VARCHAR(45) NULL,
            failed_login_attempts INT DEFAULT 0,
            account_locked_until TIMESTAMP NULL
        )
    """)
    
    # Try to add is_admin column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE")
    except mysql.connector.Error:
        # Column already exists, ignore the error
        pass
    
    # Make krishb an admin user if it exists
    try:
        cursor.execute("UPDATE users SET is_admin = TRUE WHERE username = 'krishb'")
    except mysql.connector.Error:
        # User doesn't exist yet, ignore the error
        pass
    
    # Login attempts log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50),
            ip_address VARCHAR(45) NOT NULL,
            user_agent TEXT,
            attempt_type ENUM('success', 'failed', 'blocked') NOT NULL,
            failure_reason VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_username (username),
            INDEX idx_ip_address (ip_address),
            INDEX idx_created_at (created_at)
        )
    """)
    
    # Session blacklist for JWT logout
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jwt_blacklist (
            id INT AUTO_INCREMENT PRIMARY KEY,
            jti VARCHAR(36) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

# SQLAlchemy connection URL for MySQL with pymysql driver
DATABASE_URL = f"mysql+pymysql://{mysql_user}:{mysql_password}@{MYSQL_HOST}/{MYSQL_DB}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"init_command": "SET time_zone = '+05:30'"}
)
# Configure APScheduler with MySQL jobstore
jobstores = {
    'default': SQLAlchemyJobStore(engine=engine)
}

scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()

# Tweepy client setup
client = tweepy.Client(
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    access_token=access_token,
    access_token_secret=access_token_secret
)

# JWT token blacklist check
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM jwt_blacklist WHERE jti = %s", (jti,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None

# Helper functions
def get_client_ip():
    """Get client IP address, handling proxies"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def verify_recaptcha(recaptcha_response):
    """Verify Google reCAPTCHA response"""
    data = {
        'secret': recaptcha_secret,
        'response': recaptcha_response
    }
    response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
    return response.json().get('success', False)

def get_user_by_username(username):
    """Get user from database by username"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def is_account_locked(user):
    """Check if account is currently locked"""
    if user['account_locked_until']:
        return datetime.now() < user['account_locked_until']
    return False

def log_login_attempt(username, ip_address, user_agent, attempt_type, failure_reason=None):
    """Log login attempt to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO login_attempts (username, ip_address, user_agent, attempt_type, failure_reason)
        VALUES (%s, %s, %s, %s, %s)
    """, (username, ip_address, user_agent, attempt_type, failure_reason))
    conn.commit()
    cursor.close()
    conn.close()

def update_successful_login(user_id, ip_address):
    """Update user's successful login info and reset failed attempts"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET 
            last_login_at = NOW(), 
            last_login_ip = %s, 
            failed_login_attempts = 0,
            account_locked_until = NULL
        WHERE id = %s
    """, (ip_address, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def update_failed_login(user_id, ip_address):
    """Update user's failed login info and potentially lock account"""
    MAX_ATTEMPTS = 5
    LOCK_DURATION_MINUTES = 30
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Increment failed attempts and update last failed login
    cursor.execute("""
        UPDATE users SET 
            failed_login_attempts = failed_login_attempts + 1,
            last_failed_login_at = NOW(),
            last_failed_login_ip = %s
        WHERE id = %s
    """, (ip_address, user_id))
    
    # Check if account should be locked
    cursor.execute("SELECT failed_login_attempts FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    
    if result and result[0] >= MAX_ATTEMPTS:
        cursor.execute("""
            UPDATE users SET 
                account_locked_until = DATE_ADD(NOW(), INTERVAL %s MINUTE)
            WHERE id = %s
        """, (LOCK_DURATION_MINUTES, user_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return result[0] if result else 0

# Admin helper functions
def is_admin_user():
    """Check if current authenticated user is an admin"""
    user_id = int(get_jwt_identity())
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result and result[0]

def get_username_by_id(user_id):
    """Get username by user_id"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None
    

def sync_scheduled_posts_on_startup():
    """Synchronize in-memory scheduled_posts_info with database jobs on startup"""
    global scheduled_posts_info
    
    try:
        # Get all jobs from the scheduler
        jobs = scheduler.get_jobs()
        
        print(f"Found {len(jobs)} jobs in scheduler on startup")
        
        for job in jobs:
            job_id = job.id
            
            # Skip if we already have this job in memory
            if job_id in scheduled_posts_info:
                continue
            
            # Extract job information
            if job.args and len(job.args) >= 3:
                text = job.args[0]
                user_id = job.args[2] if len(job.args) > 2 else None
                
                # Create the post info structure
                scheduled_posts_info[job_id] = {
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "full_text": text,
                    "scheduled_time": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else None,
                    "created_at": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else None,  # Approximation
                    "user_id": user_id
                }
                
                print(f"Synced job {job_id} for user {user_id}")
            else:
                print(f"Warning: Job {job_id} has unexpected args structure: {job.args}")
                
    except Exception as e:
        print(f"Error syncing scheduled posts on startup: {e}")

# Authentication Routes

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON data"}), 400

    username = data.get('username')
    password = data.get('password')
    recaptcha_response = data.get('recaptcha_response')
    totp_code = data.get('totp_code')

    ip_address = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')

    if not username or not password:
        log_login_attempt(username or 'unknown', ip_address, user_agent, 'failed', 'Missing credentials')
        return jsonify({"error": "Username and password required"}), 400

    # Get user from database
    user = get_user_by_username(username)
    if not user:
        log_login_attempt(username, ip_address, user_agent, 'failed', 'User not found')
        return jsonify({"error": "Invalid credentials"}), 401

    # Check if account is locked
    if is_account_locked(user):
        log_login_attempt(username, ip_address, user_agent, 'blocked', 'Account locked')
        return jsonify({
            "error": "Account temporarily locked due to multiple failed attempts",
            "locked_until": user['account_locked_until'].isoformat() if user['account_locked_until'] else None
        }), 423

    # Verify password
    if not check_password_hash(user['password_hash'], password):
        update_failed_login(user['id'], ip_address)
        log_login_attempt(username, ip_address, user_agent, 'failed', 'Invalid password')
        return jsonify({"error": "Invalid credentials"}), 401

    # Enhanced 2FA flow
    if user['is_2fa_enabled']:
        if not user['totp_secret']:
            # 2FA enabled but not set up yet: allow password login, trigger QR setup
            return jsonify({
                "message": "2FA setup required",
                "requires_2fa_setup": True,
                "user_id": user['id']
            }), 200
        else:
            # 2FA enabled and secret exists: require OTP
            if not totp_code:
                return jsonify({
                    "message": "2FA code required",
                    "requires_2fa": True,
                    "user_id": user['id']
                }), 200

            # 2FA step - NOW require reCAPTCHA
            if not recaptcha_response or not verify_recaptcha(recaptcha_response):
                log_login_attempt(username, ip_address, user_agent, 'failed', 'Invalid reCAPTCHA on 2FA')
                return jsonify({"error": "Invalid reCAPTCHA"}), 400

            # Verify TOTP code
            totp = pyotp.TOTP(user['totp_secret'])
            if not totp.verify(totp_code):
                update_failed_login(user['id'], ip_address)
                log_login_attempt(username, ip_address, user_agent, 'failed', 'Invalid 2FA code')
                return jsonify({"error": "Invalid 2FA code"}), 401

    # NO reCAPTCHA required for users without 2FA or initial login
    # (Remove the else block that was requiring reCAPTCHA)

    # Login successful
    access_token = create_access_token(
        identity=str(user['id']),
        additional_claims={
            'username': user['username'],
            'email': user['email'],
            'is_admin': user.get('is_admin', False)
        }
    )

    update_successful_login(user['id'], ip_address)
    log_login_attempt(username, ip_address, user_agent, 'success')

    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "is_2fa_enabled": user['is_2fa_enabled'],
            "is_admin": user.get('is_admin', False),
            "last_login_at": user['last_login_at'].isoformat() if user['last_login_at'] else None,
            "last_login_ip": user['last_login_ip']
        }
    }), 200
    
@app.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO jwt_blacklist (jti) VALUES (%s)", (jti,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Successfully logged out"}), 200

@app.route('/auth/setup-2fa', methods=['POST'])
@jwt_required()
def setup_2fa():
    user_id = int(get_jwt_identity())  # Convert string back to int
    
    # Generate TOTP secret
    secret = pyotp.random_base32()
    
    # Get user info
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Generate QR code
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user['email'],
        issuer_name="Twitter Scheduler API"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    
    # Store secret temporarily (user needs to confirm with TOTP code)
    cursor.execute("UPDATE users SET totp_secret = %s WHERE id = %s", (secret, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({
        "secret": secret,
        "qr_code": f"data:image/png;base64,{img_str}",
        "provisioning_uri": provisioning_uri
    }), 200

@app.route('/auth/confirm-2fa', methods=['POST'])
@jwt_required()
def confirm_2fa():
    data = request.json
    user_id = int(get_jwt_identity())  # Convert string back to int
    totp_code = data.get('totp_code')
    
    if not totp_code:
        return jsonify({"error": "TOTP code required"}), 400
    
    # Get user's TOTP secret
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT totp_secret FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    
    if not user or not user['totp_secret']:
        return jsonify({"error": "2FA setup not initiated"}), 400
    
    # Verify TOTP code
    totp = pyotp.TOTP(user['totp_secret'])
    if not totp.verify(totp_code):
        return jsonify({"error": "Invalid TOTP code"}), 400
    
    # Enable 2FA
    cursor.execute("UPDATE users SET is_2fa_enabled = TRUE WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({"message": "2FA enabled successfully"}), 200

@app.route('/auth/disable-2fa', methods=['POST'])
@jwt_required()
def disable_2fa():
    data = request.json
    user_id = int(get_jwt_identity())  # Convert string back to int
    password = data.get('password')
    totp_code = data.get('totp_code')
    
    if not password or not totp_code:
        return jsonify({"error": "Password and TOTP code required"}), 400
    
    # Get user info
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT password_hash, totp_secret FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Verify password
    if not check_password_hash(user['password_hash'], password):
        return jsonify({"error": "Invalid password"}), 401
    
    # Verify TOTP code
    totp = pyotp.TOTP(user['totp_secret'])
    if not totp.verify(totp_code):
        return jsonify({"error": "Invalid TOTP code"}), 401
    
    # Disable 2FA
    cursor.execute("UPDATE users SET is_2fa_enabled = FALSE, totp_secret = NULL WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({"message": "2FA disabled successfully"}), 200

@app.route('/auth/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = int(get_jwt_identity())  # Convert string back to int
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, username, email, is_2fa_enabled, is_admin, created_at, 
               last_login_at, last_login_ip, last_failed_login_at, 
               last_failed_login_ip, failed_login_attempts, account_locked_until
        FROM users WHERE id = %s
    """, (user_id,))
    user = cursor.fetchone()
    
    # Get recent login attempts
    cursor.execute("""
        SELECT attempt_type, ip_address, user_agent, failure_reason, created_at
        FROM login_attempts 
        WHERE username = (SELECT username FROM users WHERE id = %s)
        ORDER BY created_at DESC 
        LIMIT 10
    """, (user_id,))
    login_history = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Format the response
    profile_data = {
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "is_2fa_enabled": user['is_2fa_enabled'],
            "is_admin": user.get('is_admin', False),
            "created_at": user['created_at'].isoformat() if user['created_at'] else None,
            "last_login_at": user['last_login_at'].isoformat() if user['last_login_at'] else None,
            "last_login_ip": user['last_login_ip'],
            "last_failed_login_at": user['last_failed_login_at'].isoformat() if user['last_failed_login_at'] else None,
            "last_failed_login_ip": user['last_failed_login_ip'],
            "failed_login_attempts": user['failed_login_attempts'],
            "account_locked": is_account_locked(user),
            "account_locked_until": user['account_locked_until'].isoformat() if user['account_locked_until'] else None
        },
        "login_history": [
            {
                "type": attempt['attempt_type'],
                "ip_address": attempt['ip_address'],
                "user_agent": attempt['user_agent'],
                "failure_reason": attempt['failure_reason'],
                "timestamp": attempt['created_at'].isoformat()
            } for attempt in login_history
        ]
    }
    
    return jsonify(profile_data), 200

@app.route('/auth/unlock-account', methods=['POST'])
@jwt_required()
def unlock_account():
    """Admin endpoint to manually unlock an account"""
    if not is_admin_user():
        return jsonify({"error": "Unauthorized: Admin access required"}), 403
    
    data = request.json
    target_username = data.get('username')
    
    if not target_username:
        return jsonify({"error": "Username required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE users SET 
            failed_login_attempts = 0,
            account_locked_until = NULL
        WHERE username = %s
    """, (target_username,))
    
    if cursor.rowcount > 0:
        conn.commit()
        log_login_attempt(target_username, get_client_ip(), request.headers.get('User-Agent', ''), 'success', 'Account unlocked by admin')
        result = {"message": f"Account {target_username} unlocked successfully"}
        status_code = 200
    else:
        result = {"error": "User not found"}
        status_code = 404
    
    cursor.close()
    conn.close()
    
    return jsonify(result), status_code

# Admin Management Routes

@app.route('/admin/set-admin-status', methods=['POST'])
@jwt_required()
def set_admin_status():
    """Set admin status for a user (only admins can do this)"""
    if not is_admin_user():
        return jsonify({"error": "Unauthorized: Admin access required"}), 403
    
    data = request.json
    target_username = data.get('username')
    make_admin = data.get('is_admin', False)
    
    if not target_username:
        return jsonify({"error": "Username required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE users SET is_admin = %s WHERE username = %s
    """, (make_admin, target_username))
    
    if cursor.rowcount > 0:
        conn.commit()
        message = f"User {target_username} {'promoted to' if make_admin else 'removed from'} admin"
        result = {"message": message}
        status_code = 200
    else:
        result = {"error": "User not found"}
        status_code = 404
    
    cursor.close()
    conn.close()
    
    return jsonify(result), status_code

@app.route('/admin/users', methods=['GET'])
@jwt_required()
def list_all_users():
    """List all users (admin only)"""
    if not is_admin_user():
        return jsonify({"error": "Unauthorized: Admin access required"}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, username, email, is_admin, is_2fa_enabled, created_at, 
               last_login_at, failed_login_attempts, account_locked_until
        FROM users 
        ORDER BY created_at DESC
    """)
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Format the response
    users_data = []
    for user in users:
        # Count scheduled posts for each user
        user_posts_count = sum(1 for post_info in scheduled_posts_info.values() 
                              if post_info.get("user_id") == user['id'])
        
        users_data.append({
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "is_admin": user.get('is_admin', False),
            "is_2fa_enabled": user['is_2fa_enabled'],
            "created_at": user['created_at'].isoformat() if user['created_at'] else None,
            "last_login_at": user['last_login_at'].isoformat() if user['last_login_at'] else None,
            "failed_login_attempts": user['failed_login_attempts'],
            "is_account_locked": is_account_locked(user),
            "scheduled_posts_count": user_posts_count
        })
    
    return jsonify({
        "users": users_data,
        "total_users": len(users_data)
    }), 200

@app.route('/admin/delete-user-with-cleanup', methods=['DELETE'])
@jwt_required()
def delete_user_with_cleanup():
    """Delete user and clean up their scheduled jobs (admin only)"""
    if not is_admin_user():
        return jsonify({"error": "Unauthorized: Admin access required"}), 403
    
    data = request.json
    username_to_delete = data.get('username')
    
    if not username_to_delete:
        return jsonify({"error": "Username required"}), 400
    
    # Get user info before deletion
    user = get_user_by_username(username_to_delete)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    user_id_to_delete = user['id']
    
    # Find and remove user's scheduled jobs
    jobs_removed = []
    for job_id, post_info in list(scheduled_posts_info.items()):
        if post_info.get("user_id") == user_id_to_delete:
            try:
                scheduler.remove_job(job_id)
                jobs_removed.append(job_id)
                del scheduled_posts_info[job_id]
            except Exception as e:
                print(f"Error removing job {job_id}: {e}")
    
    # Delete user from database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete related records first (foreign key constraints)
    cursor.execute("DELETE FROM login_attempts WHERE username = %s", (username_to_delete,))
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id_to_delete,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({
        "message": f"User {username_to_delete} deleted successfully",
        "scheduled_jobs_removed": len(jobs_removed),
        "job_ids_removed": jobs_removed
    }), 200

@app.route('/admin/cleanup-orphaned-jobs', methods=['POST'])
@jwt_required()
def cleanup_orphaned_jobs():
    """Clean up jobs for deleted users (admin only)"""
    if not is_admin_user():
        return jsonify({"error": "Unauthorized: Admin access required"}), 403
    
    orphaned_jobs = []
    jobs_to_remove = []
    
    # Check all scheduled posts
    for job_id, post_info in list(scheduled_posts_info.items()):
        # Check if user still exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = %s", (post_info.get("user_id"),))
        user_exists = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user_exists:
            orphaned_jobs.append({
                "job_id": job_id,
                "user_id": post_info.get("user_id"),
                "scheduled_time": post_info.get("scheduled_time"),
                "text_preview": post_info.get("text", "")[:50] + "..."
            })
            
            # Remove from scheduler
            try:
                job = scheduler.get_job(job_id)
                if job:
                    scheduler.remove_job(job_id)
                    jobs_to_remove.append(job_id)
            except Exception as e:
                print(f"Error removing job {job_id}: {e}")
            
            # Remove from memory
            if job_id in scheduled_posts_info:
                del scheduled_posts_info[job_id]
    
    return jsonify({
        "message": f"Cleaned up {len(jobs_to_remove)} orphaned jobs",
        "orphaned_jobs": orphaned_jobs,
        "removed_job_ids": jobs_to_remove
    }), 200

# Protected Twitter Scheduler Routes

def split_text(text, max_length=280, cont_text=" (cont.)"):
    chunks = []
    text = text.strip()
    while len(text) > max_length:
        break_point = text.rfind(' ', 0, max_length - len(cont_text))
        if break_point == -1:
            break_point = max_length - len(cont_text)
        chunk = text[:break_point] + cont_text
        chunks.append(chunk)
        text = text[break_point:].lstrip()
    chunks.append(text)
    return chunks

scheduled_posts_info = {}

def post_thread(long_post, job_id, user_id):
    chunks = split_text(long_post)
    try:
        response = client.create_tweet(text=chunks[0])
        tweet_id = response.data['id']
        print(f"Posted first tweet with ID {tweet_id} for user {user_id}")
        
        for chunk in chunks[1:]:
            time.sleep(60)
            response = client.create_tweet(text=chunk, in_reply_to_tweet_id=tweet_id)
            tweet_id = response.data['id']
            print(f"Posted reply tweet with ID {tweet_id}")
        
        if job_id in scheduled_posts_info:
            del scheduled_posts_info[job_id]
        return True, tweet_id
    except Exception as e:
        print(f"Error posting thread: {e}")
        if job_id in scheduled_posts_info:
            del scheduled_posts_info[job_id]
        return False, str(e)

@app.route('/schedule_posts', methods=['POST'])
@jwt_required()
def schedule_posts():
    user_id = int(get_jwt_identity())  # Convert string back to int
    data = request.json
    
    if not data or 'posts' not in data:
        return jsonify({"error": "Missing 'posts' field in JSON body"}), 400

    posts = data['posts']
    scheduled_jobs = []
    
    for post in posts:
        if 'text' not in post or 'time' not in post:
            return jsonify({"error": "Each post must have 'text' and 'time' fields"}), 400
        try:
            scheduled_time = datetime.strptime(post['time'], "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            if scheduled_time <= now:
                return jsonify({"error": f"Scheduled time {post['time']} must be in the future"}), 400
            
            job = scheduler.add_job(post_thread, 'date', run_date=scheduled_time, args=[post['text'], None, user_id])
            
            scheduled_posts_info[job.id] = {
                "text": post['text'][:100] + "..." if len(post['text']) > 100 else post['text'],
                "full_text": post['text'],
                "scheduled_time": post['time'],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user_id": user_id
            }
            
            job.modify(args=[post['text'], job.id, user_id])
            scheduled_jobs.append({"post_time": post['time'], "job_id": job.id})
        except ValueError:
            return jsonify({"error": f"Invalid time format for {post['time']}. Use YYYY-MM-DD HH:MM:SS"}), 400
    
    return jsonify({"message": "Posts scheduled successfully", "jobs": scheduled_jobs}), 200

@app.route('/scheduled_posts', methods=['GET'])
@jwt_required()
def get_scheduled_posts():
    user_id = int(get_jwt_identity())  # Convert string back to int
    scheduled_posts = []
    
    # Check if current user is admin
    if is_admin_user():
        # Admin sees ALL scheduled posts
        for job_id, post_info in scheduled_posts_info.items():
            job = scheduler.get_job(job_id)
            if job:
                # Get username for this post
                post_user_id = post_info.get("user_id")
                username = get_username_by_id(post_user_id)
                
                scheduled_posts.append({
                    "job_id": job_id,
                    "text_preview": post_info["text"],
                    "full_text": post_info["full_text"],
                    "scheduled_time": post_info["scheduled_time"],
                    "created_at": post_info["created_at"],
                    "status": "scheduled",
                    "user_id": post_user_id,
                    "username": username if username else f"DELETED_USER_{post_user_id}",
                    "is_orphaned": username is None
                })
        
        return jsonify({
            "scheduled_posts": scheduled_posts, 
            "total_count": len(scheduled_posts),
            "admin_view": True,
            "orphaned_count": sum(1 for post in scheduled_posts if post.get("is_orphaned", False))
        }), 200
    
    else:
        # Regular users see only their own posts
        for job_id, post_info in scheduled_posts_info.items():
            if post_info.get("user_id") == user_id:
                job = scheduler.get_job(job_id)
                if job:
                    scheduled_posts.append({
                        "job_id": job_id,
                        "text_preview": post_info["text"],
                        "scheduled_time": post_info["scheduled_time"],
                        "created_at": post_info["created_at"],
                        "status": "scheduled"
                    })
        
        return jsonify({
            "scheduled_posts": scheduled_posts, 
            "total_count": len(scheduled_posts),
            "admin_view": False
        }), 200

@app.route('/cancel_post/<job_id>', methods=['DELETE'])
@jwt_required()
def cancel_scheduled_post(job_id):
    user_id = int(get_jwt_identity())
    
    # Check if job exists
    if job_id not in scheduled_posts_info:
        return jsonify({"error": "Scheduled post not found"}), 404
    
    post_info = scheduled_posts_info[job_id]
    
    # Admin can cancel any post, regular users can only cancel their own
    if not is_admin_user() and post_info.get("user_id") != user_id:
        return jsonify({"error": "Unauthorized: This post doesn't belong to you"}), 403
    
    try:
        scheduler.remove_job(job_id)
        del scheduled_posts_info[job_id]
        return jsonify({"message": "Scheduled post cancelled successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to cancel post: {str(e)}"}), 500

@app.route('/admin/cancel_post/<job_id>', methods=['DELETE'])
@jwt_required()
def admin_cancel_scheduled_post(job_id):
    """Admin endpoint to cancel ANY scheduled post with detailed info"""
    if not is_admin_user():
        return jsonify({"error": "Unauthorized: Admin access required"}), 403
    
    if job_id not in scheduled_posts_info:
        return jsonify({"error": "Scheduled post not found"}), 404
    
    try:
        post_info = scheduled_posts_info[job_id]
        post_user_id = post_info.get("user_id")
        username = get_username_by_id(post_user_id)
        
        scheduler.remove_job(job_id)
        del scheduled_posts_info[job_id]
        
        return jsonify({
            "message": "Scheduled post cancelled successfully by admin",
            "cancelled_post": {
                "job_id": job_id,
                "original_user": username if username else f"DELETED_USER_{post_user_id}",
                "user_id": post_user_id,
                "scheduled_time": post_info.get("scheduled_time"),
                "text_preview": post_info.get("text", "")[:100]
            }
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to cancel post: {str(e)}"}), 500

# Admin Dashboard Stats
@app.route('/admin/dashboard', methods=['GET'])
@jwt_required()
def admin_dashboard():
    """Get admin dashboard statistics"""
    if not is_admin_user():
        return jsonify({"error": "Unauthorized: Admin access required"}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get user statistics
    cursor.execute("SELECT COUNT(*) as total_users FROM users")
    total_users = cursor.fetchone()['total_users']
    
    cursor.execute("SELECT COUNT(*) as admin_users FROM users WHERE is_admin = TRUE")
    admin_users = cursor.fetchone()['admin_users']
    
    cursor.execute("SELECT COUNT(*) as users_with_2fa FROM users WHERE is_2fa_enabled = TRUE")
    users_with_2fa = cursor.fetchone()['users_with_2fa']
    
    cursor.execute("SELECT COUNT(*) as locked_users FROM users WHERE account_locked_until > NOW()")
    locked_users = cursor.fetchone()['locked_users']
    
    # Get login attempt statistics (last 24 hours)
    cursor.execute("""
        SELECT 
            COUNT(*) as total_attempts,
            SUM(CASE WHEN attempt_type = 'success' THEN 1 ELSE 0 END) as successful_logins,
            SUM(CASE WHEN attempt_type = 'failed' THEN 1 ELSE 0 END) as failed_logins,
            SUM(CASE WHEN attempt_type = 'blocked' THEN 1 ELSE 0 END) as blocked_attempts
        FROM login_attempts 
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
    """)
    login_stats = cursor.fetchone()
    
    # Get recent failed login attempts
    cursor.execute("""
        SELECT username, ip_address, failure_reason, created_at
        FROM login_attempts 
        WHERE attempt_type = 'failed' 
        ORDER BY created_at DESC 
        LIMIT 10
    """)
    recent_failures = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Calculate scheduled posts statistics
    total_scheduled_posts = len(scheduled_posts_info)
    orphaned_posts = 0
    posts_by_user = {}
    
    for job_id, post_info in scheduled_posts_info.items():
        user_id = post_info.get("user_id")
        username = get_username_by_id(user_id)
        
        if username is None:
            orphaned_posts += 1
        else:
            posts_by_user[username] = posts_by_user.get(username, 0) + 1
    
    dashboard_data = {
        "user_statistics": {
            "total_users": total_users,
            "admin_users": admin_users,
            "users_with_2fa": users_with_2fa,
            "locked_users": locked_users
        },
        "login_statistics": {
            "total_attempts_24h": login_stats['total_attempts'] or 0,
            "successful_logins_24h": login_stats['successful_logins'] or 0,
            "failed_logins_24h": login_stats['failed_logins'] or 0,
            "blocked_attempts_24h": login_stats['blocked_attempts'] or 0
        },
        "scheduled_posts_statistics": {
            "total_scheduled_posts": total_scheduled_posts,
            "orphaned_posts": orphaned_posts,
            "active_posts": total_scheduled_posts - orphaned_posts,
            "posts_by_user": posts_by_user
        },
        "recent_failed_logins": [
            {
                "username": attempt['username'],
                "ip_address": attempt['ip_address'],
                "reason": attempt['failure_reason'],
                "timestamp": attempt['created_at'].isoformat()
            } for attempt in recent_failures
        ]
    }
    
    return jsonify(dashboard_data), 200

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200

# System info endpoint (admin only)
@app.route('/admin/system-info', methods=['GET'])
@jwt_required()
def system_info():
    """Get system information (admin only)"""
    if not is_admin_user():
        return jsonify({"error": "Unauthorized: Admin access required"}), 403
    
    # Get scheduler info
    scheduler_jobs = scheduler.get_jobs()
    
    system_data = {
        "scheduler": {
            "running": scheduler.running,
            "total_jobs": len(scheduler_jobs),
            "job_stores": list(scheduler._jobstores.keys())
        },
        "database": {
            "host": MYSQL_HOST,
            "database": MYSQL_DB,
            "connection_status": "connected"
        },
        "jwt": {
            "token_expires_in_hours": app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds() / 3600
        },
        "cors": {
            "allowed_origins": ['http://localhost:3000']
        }
    }
    
    return jsonify(system_data), 200

if __name__ == '__main__':
    init_db()
    sync_scheduled_posts_on_startup()
    app.run(host='0.0.0.0', port=5000, debug=True)