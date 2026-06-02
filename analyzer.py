import json
import urllib.request
from typing import Optional
from models import (
    Chunk,
    TranslationResult,
    TranslationSuccess,
    TranslationFailure,
    JapaneseText,
    EnglishText,
)
from utils import clean_json_text


def mock_analyze(title: JapaneseText) -> TranslationFailure:
    """Safe pure mock fallback that generates a placeholder warning when API is down."""
    mock_english = EnglishText(
        "[Translation temporarily unavailable. Re-run workflow to retry.]"
    )
    mock_chunks: list[Chunk] = []
    return TranslationFailure(
        english_translation=mock_english,
        chunks=mock_chunks,
        model_used="mock",
    )


def try_models_recursively(
    models: list[str], title: JapaneseText, api_key: str
) -> TranslationResult:
    """Pure functional helper that attempts translation across available model versions."""
    if not models:
        print("All models failed. Using mock.")
        return mock_analyze(title)

    model = models[0]
    print(f"Attempting translation with model: {model}...")

    prompt = f"""You are a Japanese learning assistant. I will provide a Japanese podcast title. 
1. Translate the full title to English.
2. Break the title down word by word or phrase by phrase. For each chunk, provide the Japanese text, Romaji reading, and English meaning.

Output strictly in the following JSON format:
{{
  "english_translation": "Full english translation of the title",
  "chunks": [
    {{"japanese": "...", "romaji": "...", "meaning": "..."}}
  ]
}}

Title: {title}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    req_data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(req_data).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            text_content = res_body["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(clean_json_text(text_content))

            english = parsed.get("english_translation", "")
            chunks = parsed.get("chunks", [])

            if english and chunks:
                cleaned_chunks = [
                    Chunk(
                        japanese=JapaneseText(str(c.get("japanese", ""))),
                        romaji=str(c.get("romaji", "")),
                        meaning=EnglishText(str(c.get("meaning", ""))),
                    )
                    for c in chunks
                ]
                print(f"Successfully translated using {model}")
                return TranslationSuccess(
                    english_translation=EnglishText(str(english)),
                    chunks=cleaned_chunks,
                    model_used=model,
                )
    except Exception as e:
        err_msg = str(e)
        if api_key:
            err_msg = err_msg.replace(api_key, "REDACTED_API_KEY")
        print(f"Model {model} failed: {err_msg}")

    return try_models_recursively(models[1:], title, api_key)


def analyze_japanese(title: JapaneseText, api_key: Optional[str]) -> TranslationResult:
    """Fetches full Japanese translation & chunk breakdown via Gemini API using fallbacks.

    Returns a TranslationResult (either TranslationSuccess or TranslationFailure).
    """
    if not api_key:
        print("GEMINI_API_KEY not set. Using mock translation.")
        return mock_analyze(title)

    models = [
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ]

    return try_models_recursively(models, title, api_key)
