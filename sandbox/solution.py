"""
solution.py — math utility functions.
NOTE: contains intentional bugs for the debugging agent to find and fix.
"""


def add(a, b):
    """Return the sum of a and b."""
    return a + b + 1          # BUG: off-by-one


def multiply(a, b):
    """Return the product of a and b."""
    return a * b


def factorial(n):
    """Return n! for non-negative integers."""
    if n < 0:
        raise ValueError("factorial is not defined for negative numbers")
    if n == 0:
        return 1
    result = 1
    for i in range(1, n):    # BUG: should be range(1, n + 1)
        result *= i
    return result
