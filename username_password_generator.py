# Utilities:Random:Generator
# This module provides functionality to generate random usernames and passwords
# It also offers an interactive menu to generate and copy the random values to the clipboard

import random
import string
import pyperclip

# Utilities:Random:Username:Generation
def generate_random_username():
    """
    Generates a random username with a length between 6 and 9 characters.
    """
    length = random.randint(6, 9)
    username = ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
    return username

# Utilities:Random:Password:Generation
def generate_random_password(length=25):
    """
    Generates a random password with the specified length.
    The password consists of a combination of lowercase and uppercase letters, digits, and punctuation characters.
    If no length is provided, the default length is 25 characters.
    """
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

# Utilities:Random:Generator:Menu
def main():
    """
    Provides an interactive menu to generate and copy random usernames and passwords to the clipboard.
    """
    while True:
        print("Options:")
        print("1. Generate a random username")
        print("2. Generate a random password")
        print("3. Exit")
        choice = input("Enter your choice (1/2/3): ")

        if choice == '1':
            # Utilities:Random:Username:Generation:Example
            username = generate_random_username()
            print(f"\nUsername : {username}")
            pyperclip.copy(username)
            print("\nUsername copied to clipboard.\n")

        elif choice == '2':
            # Utilities:Random:Password:Generation:Example
            min_length = 20
            max_length = 25
            length = random.randint(min_length, max_length)
            password = generate_random_password(length)
            print(f"\nPassword: {password}")
            pyperclip.copy(password)
            print("\nPassword copied to clipboard.\n")

        elif choice == '3':
            break

        else:
            print("\nInvalid choice. Please enter 1, 2, or 3.\n")

# Utilities:Random:Generator:Main
if __name__ == "__main__":
    main()