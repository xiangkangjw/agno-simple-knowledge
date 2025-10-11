#!/usr/bin/env python3
"""Main entry point for the Knowledge Management System."""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.macos_app import main

if __name__ == "__main__":
    main()