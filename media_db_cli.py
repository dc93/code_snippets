#!/usr/bin/env python3
"""
Main entry point for Media Database CLI
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from media_db.cli import cli

if __name__ == '__main__':
    cli()
