import json
import dataclasses
from models import (
    History,
    Episode,
    Chunk,
    HISTORY_FILE,
    JapaneseText,
    EnglishText,
    JSTDateTime,
    AudioURL,
)


def load_history() -> History:
    """Pure loader that returns the current history list from file, parsed as strict dataclass instances."""
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                episodes = []
                for item in data:
                    chunks = [
                        Chunk(
                            japanese=JapaneseText(str(c.get("japanese", ""))),
                            romaji=str(c.get("romaji", "")),
                            meaning=EnglishText(str(c.get("meaning", ""))),
                        )
                        for c in item.get("chunks", [])
                    ]
                    episodes.append(
                        Episode(
                            japanese_title=JapaneseText(
                                str(item.get("japanese_title", ""))
                            ),
                            english_translation=EnglishText(
                                str(item.get("english_translation", ""))
                            ),
                            published_at=JSTDateTime(str(item.get("published_at", ""))),
                            audio_url=AudioURL(str(item.get("audio_url", ""))),
                            chunks=chunks,
                            is_mock=bool(item.get("is_mock", False)),
                            translation_model=str(
                                item.get("translation_model", "mock")
                            ),
                        )
                    )
                return episodes
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return []


def save_history(history: History) -> None:
    """Side-effect function that persists the history list to file, sorted by date descending."""
    try:
        # Sort history by published_at descending to keep chronological order
        sorted_history = sorted(history, key=lambda ep: ep.published_at, reverse=True)
        # Enforce history limit of latest 100 items
        truncated_history = sorted_history[:100]

        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(
                [dataclasses.asdict(ep) for ep in truncated_history],
                f,
                indent=2,
                ensure_ascii=False,
            )
    except Exception as e:
        print(f"Failed to save history: {e}")
