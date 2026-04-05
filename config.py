"""Load settings from environment. No hardcoded secrets or URLs."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    supabase_url: str
    supabase_key: str
    sample_book_id: str
    max_upload_bytes: int


def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()
    sample_book_id = os.getenv("SAMPLE_BOOK_ID", "sample-parable").strip()
    max_mb = int(os.getenv("MAX_UPLOAD_MB", "10").strip() or "10")
    max_upload_bytes = max(1, max_mb) * 1024 * 1024

    missing = [
        name
        for name, val in (
            ("BOT_TOKEN", bot_token),
            ("SUPABASE_URL", supabase_url),
            ("SUPABASE_KEY", supabase_key),
        )
        if not val
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in values."
        )

    return Settings(
        bot_token=bot_token,
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        sample_book_id=sample_book_id,
        max_upload_bytes=max_upload_bytes,
    )
