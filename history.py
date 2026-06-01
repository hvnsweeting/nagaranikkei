import os
import json
from models import History, HISTORY_FILE


def load_history() -> History:
    """Pure loader that returns the current history list from file."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def save_history(history: History) -> None:
    """Side-effect function that persists the history list to file, sorted by date descending."""
    try:
        # Sort history by published_at descending to keep chronological order
        sorted_history = sorted(
            history, key=lambda ep: str(ep.get("published_at", "")), reverse=True
        )
        # Enforce history limit of latest 100 items
        truncated_history = sorted_history[:100]

        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(truncated_history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save history: {e}")
