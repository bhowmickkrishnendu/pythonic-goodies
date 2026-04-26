# Concept: *args and **kwargs
# What it does: Accepts variable number of inputs

# *args example
def sum_all(*args):
    total = 0
    for num in args:
        total += num
    return total

print(sum_all(1, 2, 3))

# **kwargs example
def config(**kwargs):
    for k, v in kwargs.items():
        print(f"{k} = {v}")

config(env="prod", version="v1")

# Combined
def demo(*args, **kwargs):
    print(args)
    print(kwargs)

demo(1, 2, a=10, b=20)

# Practice:
# 1. Sum numbers using *args
# 2. Print config using **kwargs

# Time suggestion: 45 min hands-on