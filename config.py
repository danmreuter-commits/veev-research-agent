"""
Configuration: loads all settings from environment variables (via .env file).
All values are validated at import time so failures surface immediately.
"""

import os
import sys
from pathlib import Path

# Load .env if present (no-op if python-dotenv is not installed or file missing)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # python-dotenv not installed; rely on real env vars

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# ── Email (SMTP) ──────────────────────────────────────────────────────────────
EMAIL_FROM:      str = os.getenv("EMAIL_FROM", "")
EMAIL_TO:        str = os.getenv("EMAIL_TO", "")       # comma-separated for multiple recipients
EMAIL_SMTP_HOST: str = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT: int = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SMTP_USER: str = os.getenv("EMAIL_SMTP_USER", "")
EMAIL_SMTP_PASS: str = os.getenv("EMAIL_SMTP_PASS", "")

# ── Research settings ─────────────────────────────────────────────────────────
# How many days back to consider a finding "already sent" (deduplication window)
LOOKBACK_DAYS: int = int(os.getenv("LOOKBACK_DAYS", "7"))

# ── Airtable (optional — for searchable database of daily briefs) ──────────────
AIRTABLE_API_KEY:   str = os.getenv("AIRTABLE_API_KEY", "")
AIRTABLE_BASE_ID:   str = os.getenv("AIRTABLE_BASE_ID", "")
AIRTABLE_TABLE_NAME: str = os.getenv("AIRTABLE_TABLE_NAME", "VEEV Daily Briefs")

# ── Validation ────────────────────────────────────────────────────────────────
def validate() -> None:
    """Fail fast if required settings are missing."""
    if not ANTHROPIC_API_KEY:
        sys.exit(
            "ERROR: ANTHROPIC_API_KEY is not set.\n"
            "Set it in your .env file or as an environment variable."
        )
