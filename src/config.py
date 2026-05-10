import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

PBRAIN_URL = os.getenv("PBRAIN_URL")
PBRAIN_ID = os.getenv("PBRAIN_ID")
PBRAIN_PW = os.getenv("PBRAIN_PW")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_REPO = os.getenv("GITHUB_REPO")

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = ROOT / "screenshots"
DOCS_DIR = ROOT / "docs"


def get_week_ranges(today: datetime = None):
    """直近完了週（月-日）と先々週を返す"""
    if today is None:
        today = datetime.now()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    last_sunday = this_monday - timedelta(days=1)
    two_weeks_monday = this_monday - timedelta(days=14)
    two_weeks_sunday = this_monday - timedelta(days=8)
    return {
        "lastweek": (last_monday, last_sunday),
        "twoweeksago": (two_weeks_monday, two_weeks_sunday),
    }
