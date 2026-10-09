"""Shared setup for the unit tests: the modules import each other by bare name, so the source folder goes on sys.path.

The tests use invented data only. They never read or write the live input, the reference CSVs or any client workbook.
"""
import os
import sys

SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)
