"""Vercel serverless entrypoint.

Vercel imports this module and serves the exported ASGI `app` for every
request rewritten from /api/*. The FastAPI routes already carry the /api
prefix, so no mounting changes are needed.
"""
import sys
from pathlib import Path

# Make backend/app importable inside the serverless bundle.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app as app  # noqa: E402, F401 — Vercel serves this ASGI app
