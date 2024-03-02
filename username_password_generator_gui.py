import tkinter as tk
import random
import string
import pyperclip

# Utilities:Random:Username:Generation
def generate_random_username():
    """ Generates a random username with a length between 6 and 9 characters. """
    length = random.randint(6, 9)
    username = ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
    return username

# Utilities:Random:Password:Generation
def generate_random_password(length=25):
    """ Generates a random password with the specified length. The password consists of a combination of lowercase and uppercase letters, digits, and punctuation characters. If no length is provided, the default length is 25 characters. """
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

# Utilities:Random:Generator:GUI
class RandomGenerator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Random Generator")
        self.geometry("400x200")

        # Create labels
        self.result_label = tk.Label(self, text="", font=("Arial", 14))
        self.result_label.pack(pady=10)

        # Create buttons
        self.username_button = tk.Button(self, text="Generate Username", command=self.generate_username)
        self.username_button.pack(pady=5)

        self.password_button = tk.Button(self, text="Generate Password", command=self.generate_password)
        self.password_button.pack(pady=5)

    def generate_username(self):
        username = generate_random_username()
        self.result_label.config(text=f"Username: {username}")
        pyperclip.copy(username)

    def generate_password(self):
        password = generate_random_password()
        self.result_label.config(text=f"Password: {password}")
        pyperclip.copy(password)

# Utilities:Random:Generator:Main
if __name__ == "__main__":
    app = RandomGenerator()
    app.mainloop()