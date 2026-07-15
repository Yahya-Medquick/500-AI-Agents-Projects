"""
Unit Test Generator Agent using Gemini Key Rotation.

Analyzes Python code and generates comprehensive pytest test suites
covering happy paths, edge cases, and error conditions.
"""

import argparse
import base64
import os
import re

from docx import Document
from dotenv import load_dotenv
from fpdf import FPDF
from langchain_core.messages import HumanMessage, SystemMessage
from pptx import Presentation

# Import the key rotator helper at the top
from scripts.gemini_rotator import get_gemini_llm

load_dotenv()

TEST_PROMPT = """You are an expert Python test engineer. Generate a comprehensive pytest test suite for the provided code.

Requirements:
1. Use pytest fixtures where appropriate
2. Test happy paths (normal expected inputs)
3. Test edge cases (boundary values, empty inputs)
4. Test error conditions (invalid inputs, exceptions)
5. Use descriptive test names: `test_function_name_scenario`
6. Add brief docstrings to each test
7. Use `pytest.mark.parametrize` for repetitive tests
8. Mock external dependencies (API calls, file I/O, DB)
9. Aim for 90%+ code coverage

Output ONLY the complete test file content, ready to run with `pytest`."""

SAMPLE_CODE = '''
def calculate_discount(price: float, discount_percent: float) -> float:
    """Calculate discounted price."""
    if price < 0:
        raise ValueError("Price cannot be negative")
    if not 0 <= discount_percent <= 100:
        raise ValueError("Discount must be between 0 and 100")
    return price * (1 - discount_percent / 100)


def find_longest_word(text: str) -> str:
    """Find the longest word in a text string."""
    if not text or not text.strip():
        return ""
    words = text.split()
    return max(words, key=len)


class ShoppingCart:
    def __init__(self):
        self.items = {}

    def add_item(self, name: str, price: float, quantity: int = 1):
        if price < 0:
            raise ValueError("Price cannot be negative")
        if quantity < 1:
            raise ValueError("Quantity must be at least 1")
        if name in self.items:
            self.items[name]["quantity"] += quantity
        else:
            self.items[name] = {"price": price, "quantity": quantity}

    def remove_item(self, name: str):
        if name not in self.items:
            raise KeyError(f"Item '{name}' not in cart")
        del self.items[name]

    def total(self) -> float:
        return sum(item["price"] * item["quantity"] for item in self.items.values())
'''


def generate_tests(code: str, filename: str = "module") -> str:
    # Uses key rotator with gemini-3.5-flash
    llm = get_gemini_llm(model="gemini-3.5-flash", temperature=0)
    messages = [
        SystemMessage(content=TEST_PROMPT),
        HumanMessage(content=f"Generate tests for this Python code (from `{filename}`):\n\n```python\n{code}\n```"),
    ]
    response = llm.invoke(messages)
    return response.content


def format_report_markdown(filename: str, tests_code: str) -> str:
    return f"""# Unit Test Generation Report: {filename}

### Generated Test Suite
```python
{tests_code}
