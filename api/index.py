"""Serverless entry point used by Vercel.

Vercel imports the ``app`` variable from this file.  The actual Flask application
lives in dashboard/app.py, so this tiny adapter first makes the project root
importable and then exposes that Flask object.
"""
import os
import sys

# ``__file__`` is api/index.py; going up twice reaches the project root.
# Adding it to sys.path lets this serverless file import ``dashboard.app``.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The deployment platform looks specifically for a variable named ``app``.
from dashboard.app import app
