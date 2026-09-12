"""
Shared pytest fixtures / setup for the whole test suite.
"""

import sys
import os

# Ensure the project root is importable when running `pytest` from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
