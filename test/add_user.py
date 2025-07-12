import mysql.connector
import bcrypt
import getpass
import os

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'your-mysql-password'),
    'database': os.environ.get('DB_NAME', 'stock_analysis_db'),
}

def hash_password(password):
    """Hash a password for storing"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def add_user():
    print("\n=== Add New User to Stock Analysis App ===\n")
    
    # Get user input
    username = input("Enter username: ")
    email = input("Enter email: ")
    password = getpass.getpass("Enter password: ")
    confirm_password = getpass.getpass("Confirm password: ")
    
    # Validate input
    if not username or not email or not password:
        print("Error: All fields are required")
        return
    
    if password != confirm_password:
        print("Error: Passwords do not match")
        return
    
    # Hash the password
    password_hash = hash_password(password)
    
    try:
        # Connect to the database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check if username or email already exists
        cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print("Error: Username or email already exists")
            conn.close()
            return
        
        # Insert the new user
        cursor.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)",
            (username, password_hash.decode('utf-8'), email)
        )
        
        conn.commit()
        print(f"\nSuccess! User '{username}' has been added to the database.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    add_user()