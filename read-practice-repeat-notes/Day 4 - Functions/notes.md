# Concept: Functions
# What it does: Reusable blocks of code

# Basic function
def greet():
    print("Hello")

greet()

# With arguments
def greet(name):
    print(f"Hello {name}")

greet("DevOps")

# Return value
def add(a, b):
    return a + b

result = add(2, 3)
print(result)

# Default argument
def deploy(service, env="dev"):
    print(f"{service} -> {env}")

deploy("api")
deploy("api", "prod")

# Practice:
# 1. Create a function to check CPU
# 2. Return "High" or "Normal"
# 3. Call it with different values

# Time suggestion: 45–60 min hands-on