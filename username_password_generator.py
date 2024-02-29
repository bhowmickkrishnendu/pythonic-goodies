import random
import string
import pyperclip

def generate_random_username():
    length = random.randint(6, 9)
    username = ''.join(random.choice(string.ascii_lowercase) for _ in range (length))
    return username

def generate_random_password(length=25):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range (length))
    return password

def main():
    while True:
        print("Options:")
        print("1. Generate a random username")
        print("2. Generate a random password")
        print("3. Exit")

        choice = input("Enter your choice (1/2/3): ")

        if choice == '1':
            username = generate_random_username()
            print(f"\nUsername :  {username}")
            pyperclip.copy(username)
            print("\nUsername copied to clipboard.\n")
        elif choice == '2':
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

if __name__ == "__main__":
    main()