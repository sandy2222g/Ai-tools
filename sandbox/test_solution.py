"""
test_solution.py — tests for solution.py
"""
import pytest
from solution import add, multiply, factorial


# ── add ───────────────────────────────────────────────────────────────────────

def test_add_positive():
    assert add(2, 3) == 5

def test_add_zero():
    assert add(0, 0) == 0

def test_add_negative():
    assert add(-1, -1) == -2


# ── multiply ──────────────────────────────────────────────────────────────────

def test_multiply_basic():
    assert multiply(3, 4) == 12

def test_multiply_by_zero():
    assert multiply(5, 0) == 0


# ── factorial ─────────────────────────────────────────────────────────────────

def test_factorial_zero():
    assert factorial(0) == 1

def test_factorial_one():
    assert factorial(1) == 1

def test_factorial_five():
    assert factorial(5) == 120

def test_factorial_negative():
    with pytest.raises(ValueError):
        factorial(-1)
