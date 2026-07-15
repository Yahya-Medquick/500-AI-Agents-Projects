"""
Documentation Writer Agent using Gemini Key Rotation.

Generates comprehensive documentation for Python modules:
README, API reference, docstrings, and usage examples.
"""

import argparse
import ast
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


def extract_structure(code: str) -> str:
    """Extract functions, classes, and their signatures from Python code."""
    try:
        tree = ast.parse(code)
        structure = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                args = [a.arg for a in node.args.args]
                structure.append(f"def {node.name}({', '.join(args)})")
            elif isinstance(node, ast.ClassDef):
                structure.append(f"class {node.name}:")
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        args = [a.arg for a in item.args.args]
                        structure.append(f"  def {item.name}({', '.join(args)})")

        return "\n".join(structure)
    except Exception:
        return "Could not parse structure"


README_PROMPT = """You are a technical documentation expert. Generate a complete, professional README.md for this Python module.

Include:
1. Module title and one-line description
2. Features list (bullet points)
3. Installation section
4. Quick Start with working code example
5. API Reference (each public function/class with parameters, return type, example)
6. Configuration (environment variables if any)
7. Error Handling section

Write in clear, developer-friendly markdown. Be specific and concrete."""

DOCSTRING_PROMPT = """Add comprehensive Google-style docstrings to every function and class that lacks them.

Format:
