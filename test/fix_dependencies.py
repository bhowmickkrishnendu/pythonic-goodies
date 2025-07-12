#!/usr/bin/env python3

import subprocess
import sys

def fix_dependencies():
    print("Installing compatible versions of Flask and Werkzeug...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully!")
        print("\nYou can now run your application with:")
        print("python app.py")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False
    return True

if __name__ == "__main__":
    fix_dependencies()