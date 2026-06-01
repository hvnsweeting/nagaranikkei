from typing import Any, Final

# Project Configuration Constants
RSS_URL: Final[str] = "https://feeds.megaphone.fm/nagara"
HISTORY_FILE: Final[str] = "history.json"
DIST_DIR: Final[str] = "dist"
BASE_URL: Final[str] = "https://hvnsweeting.github.io/nagaranikkei"

# Modern PEP 585 Type Aliases
Chunk = dict[str, str]
Episode = dict[str, Any]
History = list[Episode]
