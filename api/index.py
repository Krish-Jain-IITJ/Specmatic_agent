import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so imports work when Vercel runs this file
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load local .env if present (useful for local Vercel preview)
try:
	from dotenv import load_dotenv
	load_dotenv(str(ROOT / '.env'))
except Exception:
	pass

from main import app

__all__ = ["app"]
