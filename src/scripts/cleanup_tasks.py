"""
Cleanup tasks for URL shortener.

This script can be scheduled to run periodically to:
1. Remove expired URLs
2. Remove unused URLs based on configured threshold

Usage:
    python -m src.scripts.cleanup_tasks
"""

import sys
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.app.db.session import get_db
from src.app.services.url_service import cleanup_expired_urls, cleanup_unused_links
from src.app.core.config import settings


def run_cleanup():
    """Run all cleanup tasks."""
    db = next(get_db())

    try:
        expired_count = cleanup_expired_urls(db)
        print(f"Cleaned up {expired_count} expired URLs")

        unused_count = cleanup_unused_links(db, settings.UNUSED_LINKS_THRESHOLD_DAYS)
        print(
            f"Cleaned up {unused_count} unused URLs (not accessed in {settings.UNUSED_LINKS_THRESHOLD_DAYS} days)"
        )

        return expired_count + unused_count
    finally:
        db.close()


if __name__ == "__main__":
    total_cleaned = run_cleanup()
    print(f"Total cleaned URLs: {total_cleaned}")
