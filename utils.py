import os
import email.utils
from datetime import datetime, timezone, timedelta
from typing import Optional


def read_from_env_file(key: str) -> Optional[str]:
    """Reads a key from a local .env file if it exists."""
    if os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(key + "="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return None


def get_api_key() -> Optional[str]:
    """Retrieves the Gemini API key from environment variables or .env file."""
    return (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GEMINI_API_TOKEN")
        or read_from_env_file("GEMINI_API_KEY")
        or read_from_env_file("GEMINI_API_TOKEN")
    )


def clean_json_text(text: str) -> str:
    """Pure function that strips markdown code fence wrappers from a JSON string if present.

    Uses fast O(N) string slicing to completely eliminate ReDoS risks.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        newline_idx = stripped.find("\n")
        if newline_idx != -1:
            stripped = stripped[newline_idx + 1 :]
        else:
            stripped = stripped[3:]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    return stripped.strip()


def sanitize_audio_url(url: Optional[str]) -> str:
    """Pure function that ensures the URL strictly uses http:// or https:// to prevent XSS."""
    if not url:
        return "https://www.radionikkei.jp/nagara/"
    trimmed = url.strip()
    if trimmed.startswith("http://") or trimmed.startswith("https://"):
        return trimmed
    return "https://www.radionikkei.jp/nagara/"


def parse_date(pub_date_str: str) -> str:
    """Pure function that converts RFC 2822 date string into standard ISO format in JST (UTC+9)."""
    tz_jst = timezone(timedelta(hours=9))
    try:
        dt = email.utils.parsedate_to_datetime(pub_date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_jst = dt.astimezone(tz_jst)
        return dt_jst.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now(tz_jst).strftime("%Y-%m-%d %H:%M:%S")
