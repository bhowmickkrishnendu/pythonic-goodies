# Concept: Conditionals (if/else)
# What it does: Executes logic based on conditions

cpu = 85

if cpu > 80:
    print("High CPU")
else:
    print("Normal")

# Multiple conditions
memory = 70
if cpu > 80 and memory > 60:
    print("High load")

# elif example
status_code = 404

if status_code == 200:
    print("OK")
elif status_code == 404:
    print("Not Found")
else:
    print("Error")

# Practice:
# 1. Write condition for production vs non-production
# 2. Combine 2 conditions using AND
# 3. Use elif for 3 cases

# Time suggestion: 30–40 min hands-on