# Concept: Lists, Dicts, Sets, Tuples
# What it does: Store collections of data

# List
services = ["api", "auth"]
services.append("db")

# Dict
config = {"env": "prod", "replicas": 2}

# Tuple
coords = (10, 20)

# Set
ids = {1, 2, 2, 3}

# Loop list
for s in services:
    print(s)

# Loop dict
for k, v in config.items():
    print(k, v)

# Practice:
# 1. Create list of services
# 2. Create config dict
# 3. Loop and print both

# Time suggestion: 1 hour hands-on