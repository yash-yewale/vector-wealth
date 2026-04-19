# conftest.py — shared test configuration
import sys
from pathlib import Path

# Ensure backend directory is in the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
