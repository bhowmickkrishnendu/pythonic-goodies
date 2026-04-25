# Concept: Loops (for, while)
# What it does: Repeats tasks

# for loop
for i in range(3):
    print(i)

# range with start/end
for i in range(1, 4):
    print(i)

# loop through string
for c in "ai":
    print(c)

# while loop
count = 0
while count < 3:
    print(count)
    count += 1

# break
for i in range(5):
    if i == 3:
        break
    print(i)

# continue
for i in range(5):
    if i == 2:
        continue
    print(i)

# Practice:
# 1. Loop from 1 to 10
# 2. Print only even numbers
# 3. Simulate retry attempts

# Time suggestion: 40–60 min hands-on