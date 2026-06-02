from dataclasses import dataclass
from typing import Any, Final, NewType, Union

# Project Configuration Constants
RSS_URL: Final[str] = "https://feeds.megaphone.fm/nagara"
HISTORY_FILE: Final[str] = "history.json"
DIST_DIR: Final[str] = "dist"
BASE_URL: Final[str] = "https://hvnsweeting.github.io/nagaranikkei"

# Rust-like NewType wrappers for semantic boundaries
JapaneseText = NewType("JapaneseText", str)
EnglishText = NewType("EnglishText", str)
JSTDateTime = NewType("JSTDateTime", str)
AudioURL = NewType("AudioURL", str)


@dataclass(frozen=True)
class Chunk:
    japanese: JapaneseText
    romaji: str
    meaning: EnglishText


@dataclass(frozen=True)
class Episode:
    japanese_title: JapaneseText
    english_translation: EnglishText
    published_at: JSTDateTime
    audio_url: AudioURL
    chunks: list[Chunk]
    is_mock: bool = False
    translation_model: str = "mock"


# Algebraic Data Types (ADTs) for API outputs
@dataclass(frozen=True)
class TranslationSuccess:
    english_translation: EnglishText
    chunks: list[Chunk]
    model_used: str


@dataclass(frozen=True)
class TranslationFailure:
    english_translation: EnglishText
    chunks: list[Chunk]
    model_used: str = "mock"


TranslationResult = Union[TranslationSuccess, TranslationFailure]

# Modern PEP 585 Type Aliases
History = list[Episode]
