#!/usr/bin/env python3
import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
import re
import html
from typing import Optional, Any, Final

# Type Aliases utilizing modern PEP 585 generics
Chunk = dict[str, str]
Episode = dict[str, Any]
History = list[Episode]

RSS_URL: Final[str] = "https://feeds.megaphone.fm/nagara"
HISTORY_FILE: Final[str] = "history.json"
DIST_DIR: Final[str] = "dist"


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


def parse_date(pub_date_str: str) -> str:
    """Pure function that converts RFC 2822 date string into standard ISO format."""
    try:
        clean_date_str = re.sub(r"\s+[\+\-]\d{4}$", "", pub_date_str)
        clean_date_str = re.sub(r"\s+GMT$", "", clean_date_str)
        dt = datetime.strptime(clean_date_str.strip(), "%a, %d %b %Y %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def parse_xml_to_episodes_metadata(
    xml_data: bytes, limit: int = 5
) -> list[tuple[str, str, str]]:
    """Pure parser that extracts the first N episodes (title, pubDate, audio_url) from RSS bytes."""
    try:
        root = ET.fromstring(xml_data)
        items = root.findall(".//item")[:limit]
        metadata_list = []
        for item in items:
            title_elem = item.find("title")
            pub_date_elem = item.find("pubDate")
            link_elem = item.find("link")
            enclosure_elem = item.find("enclosure")

            title = title_elem.text if title_elem is not None else None
            pub_date_str = pub_date_elem.text if pub_date_elem is not None else None

            link = link_elem.text if link_elem is not None else None
            enclosure_url = (
                enclosure_elem.get("url") if enclosure_elem is not None else None
            )

            audio_url = link if link and link.strip() else enclosure_url
            sanitized_audio = sanitize_audio_url(audio_url)

            if title and pub_date_str:
                metadata_list.append(
                    (title.strip(), pub_date_str.strip(), sanitized_audio)
                )

        return metadata_list
    except Exception as e:
        print(f"Failed to parse RSS XML: {e}")
    return []


def mock_analyze(title: str) -> tuple[str, list[Chunk]]:
    """Safe pure mock fallback that generates a placeholder warning when API is down."""
    mock_english = "[Translation temporarily unavailable. Re-run workflow to retry.]"
    mock_chunks: list[Chunk] = []
    return mock_english, mock_chunks


def try_models_recursively(
    models: list[str], title: str, api_key: str
) -> tuple[str, list[Chunk], str, bool]:
    """Pure functional helper that attempts translation across available model versions."""
    if not models:
        print("All models failed. Using mock.")
        english, chunks = mock_analyze(title)
        return english, chunks, "mock", True

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
                    {
                        "japanese": str(c.get("japanese", "")),
                        "romaji": str(c.get("romaji", "")),
                        "meaning": str(c.get("meaning", "")),
                    }
                    for c in chunks
                ]
                print(f"Successfully translated using {model}")
                return english, cleaned_chunks, model, False
    except Exception as e:
        err_msg = str(e)
        if api_key:
            err_msg = err_msg.replace(api_key, "REDACTED_API_KEY")
        print(f"Model {model} failed: {err_msg}")

    return try_models_recursively(models[1:], title, api_key)


def analyze_japanese(
    title: str, api_key: Optional[str]
) -> tuple[str, list[Chunk], str, bool]:
    """Fetches full Japanese translation & chunk breakdown via Gemini API using fallbacks.

    Returns (english_translation, chunks, model_used, is_mock).
    """
    if not api_key:
        print("GEMINI_API_KEY not set. Using mock translation.")
        english, chunks = mock_analyze(title)
        return english, chunks, "mock", True

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


def format_chunk_html(c: Chunk) -> str:
    """Pure formatter that transforms a vocabulary chunk to HTML list items."""
    jp_encoded = urllib.parse.quote_plus(c.get("japanese", ""))
    return f"""              <div class="chunk">
                <dt>
                  <a href="https://jisho.org/search/{jp_encoded}" target="_blank" rel="noopener noreferrer" class="chunk-jp-link">
                    <span class="chunk-jp">{html.escape(c.get("japanese", ""))}</span>
                  </a>
                  <span class="chunk-ro">{html.escape(c.get("romaji", ""))}</span>
                </dt>
                <dd class="chunk-en">{html.escape(c.get("meaning", ""))}</dd>
              </div>"""


def format_episode_card(ep: Episode) -> str:
    """Pure formatter that transforms an Episode card structure to beautiful dynamic HTML."""
    chunks_list = ep.get("chunks", [])
    chunks_html = ""
    if chunks_list:
        chunks_html = "\n".join(format_chunk_html(c) for c in chunks_list)
        chunks_container = f"""            <dl class="chunks-container">
{chunks_html}
            </dl>"""
    else:
        chunks_container = ""

    date_formatted = ep.get("published_at", "")[:10]
    audio_url = ep.get("audio_url", "") or "https://www.radionikkei.jp/nagara/"

    is_mock = ep.get("is_mock", False)
    title_class = "english-title translation-pending" if is_mock else "english-title"

    return f"""          <div class="episode-card">
            <div class="card-meta">
              <span class="date">{html.escape(date_formatted)}</span>
              <a href="{html.escape(audio_url)}" target="_blank" rel="noopener noreferrer" class="podcast-link">
                Podcast Link
              </a>
            </div>
            <h2 class="japanese-title">
              {html.escape(ep.get("japanese_title", ""))}
              <button onclick="speakTitle(this)" data-title="{html.escape(ep.get("japanese_title", ""))}" class="listen-badge" title="Read title aloud">
                🔊 Speech to Text
              </button>
            </h2>
            <p class="{title_class}">{html.escape(ep.get("english_translation", ""))}</p>
{chunks_container}
          </div>"""


def render_html_content(cards_html: str) -> str:
    """Pure formatter that produces the full-page static index.html dashboard template."""
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ながら日経 Podcast Tracker</title>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

      :root {{
        --bg-color: #0f172a;
        --card-bg: #1e293b;
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        --accent: #38bdf8;
        --accent-glow: rgba(56, 189, 248, 0.2);
        --border-color: #334155;
      }}
      body {{
        background-color: var(--bg-color);
        color: var(--text-main);
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        margin: 0;
        padding: 0;
        line-height: 1.6;
        -webkit-font-smoothing: antialiased;
      }}
      .container {{
        max-width: 800px;
        margin: 0 auto;
        padding: 40px 20px;
      }}
      header {{
        text-align: center;
        margin-bottom: 50px;
      }}
      h1 {{
        font-size: 2.5rem;
        margin: 0;
        background: linear-gradient(135deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
      }}
      p.subtitle {{
        color: var(--text-muted);
        font-size: 1.1rem;
      }}
      .episode-card {{
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 30px;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
      }}
      .card-meta {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 10px;
      }}
      .date {{
        font-size: 0.9rem;
        color: var(--accent);
        text-transform: uppercase;
        letter-spacing: 1px;
        display: inline-block;
      }}
      .podcast-link {{
        font-size: 0.85rem;
        color: var(--text-muted);
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        transition: color 0.2s ease;
      }}
      .podcast-link:hover {{
        color: var(--accent);
        text-decoration: underline;
      }}
      .japanese-title {{
        font-size: 1.5rem;
        margin: 0 0 10px 0;
        font-weight: 600;
        letter-spacing: 0.5px;
      }}
      .english-title {{
        font-size: 1.1rem;
        color: var(--text-muted);
        margin: 0 0 25px 0;
        font-style: italic;
      }}
      .english-title.translation-pending {{
        color: #f59e0b;
        opacity: 0.8;
      }}
      .chunks-container {{
        display: flex;
        flex-direction: column;
        background: rgba(255, 255, 255, 0.01);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        overflow: hidden;
        margin-top: 15px;
        margin-bottom: 0;
        padding: 0;
      }}
      .chunk {{
        display: grid;
        grid-template-columns: 220px 1fr;
        align-items: center;
        gap: 20px;
        padding: 16px 20px;
        border-bottom: 1px solid var(--border-color);
        margin: 0;
        transition: background-color 0.2s ease;
        cursor: default;
      }}
      .chunk:last-child {{
        border-bottom: none;
      }}
      .chunk:hover {{
        background-color: rgba(255, 255, 255, 0.03);
      }}
      .chunk dt, .chunk dd {{
        margin: 0;
        padding: 0;
      }}
      .chunk dt {{
        display: flex;
        flex-direction: column;
        gap: 4px;
      }}
      .chunk-jp-link {{
        text-decoration: none;
        color: #fff;
        transition: color 0.2s ease;
      }}
      .chunk-jp-link:hover {{
        color: var(--accent);
        text-decoration: underline;
      }}
      .chunk-jp {{
        font-size: 1.25rem;
        font-weight: 600;
        color: inherit;
      }}
      .chunk-ro {{
        font-size: 0.85rem;
        color: var(--accent);
        letter-spacing: 0.5px;
      }}
      .chunk-en {{
        font-size: 1rem;
        color: var(--text-main);
        line-height: 1.5;
      }}
      .listen-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: var(--accent-glow);
        border: 1px solid var(--accent);
        color: var(--accent);
        font-size: 0.85rem;
        padding: 4px 12px;
        border-radius: 9999px;
        margin-left: 12px;
        text-decoration: none;
        vertical-align: middle;
        font-weight: 500;
        cursor: pointer;
        font-family: inherit;
        transition: background-color 0.2s ease, transform 0.2s ease;
      }}
      .listen-badge:hover {{
        background: var(--accent);
        color: var(--bg-color);
        transform: scale(1.05);
      }}
      .listen-badge:disabled {{
        opacity: 0.7;
        cursor: not-allowed;
      }}
      .empty-state {{
        text-align: center;
        padding: 50px;
        color: var(--text-muted);
        border: 1px dashed var(--border-color);
        border-radius: 16px;
      }}
      .rss-info {{
        text-align: center;
        margin-top: 40px;
        padding: 20px;
        background: rgba(255,255,255,0.02);
        border: 1px solid var(--border-color);
        border-radius: 12px;
      }}
      .rss-link {{
        color: var(--accent);
        font-weight: 600;
        text-decoration: none;
      }}
      .rss-link:hover {{
        text-decoration: underline;
      }}
      .pagination-container {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 20px;
        margin-top: 40px;
        margin-bottom: 20px;
      }}
      .page-btn {{
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        color: var(--text-main);
        padding: 10px 20px;
        border-radius: 8px;
        cursor: pointer;
        font-weight: 600;
        transition: background-color 0.2s ease, border-color 0.2s ease;
      }}
      .page-btn:hover:not(:disabled) {{
        background: rgba(255, 255, 255, 0.05);
        border-color: var(--accent);
      }}
      .page-btn:disabled {{
        opacity: 0.5;
        cursor: not-allowed;
      }}
      .page-info {{
        font-size: 1rem;
        color: var(--text-muted);
        font-weight: 500;
      }}
      @media (max-width: 600px) {{
        .chunk {{
          grid-template-columns: 1fr;
          gap: 8px;
          padding: 14px 16px;
        }}
        .listen-badge {{
          margin-left: 0;
          margin-top: 8px;
          display: inline-flex;
        }}
      }}
    </style>
  </head>
  <body>
    <div class="container">
      <header>
        <h1>ながら日経 Tracker</h1>
        <p class="subtitle">Daily Japanese learning through podcast titles</p>
      </header>

      <main>
        {cards_html}
      </main>

      <div class="pagination-container" id="pagination-controls">
        <button id="prev-btn" class="page-btn">Previous</button>
        <span id="page-info" class="page-info">Page 1 of 1</span>
        <button id="next-btn" class="page-btn">Next</button>
      </div>

      <footer class="rss-info">
        <p>💡 Want to learn inside your favorite RSS reader? Subscribe to our custom vocabulary feed:</p>
        <p>🔗 <a class="rss-link" href="rss.xml" target="_blank">Subscribe to rss.xml Feed</a></p>
      </footer>
    </div>

    <script>
      function speakTitle(btn) {{
        const text = btn.getAttribute('data-title');
        if ('speechSynthesis' in window) {{
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(text);
          const voices = window.speechSynthesis.getVoices();
          const jaVoice = voices.find(voice => voice.lang.startsWith('ja'));
          if (jaVoice) {{
            utterance.voice = jaVoice;
          }}
          utterance.lang = 'ja-JP';
          
          const originalText = btn.innerHTML;
          btn.innerHTML = '🔊 Speaking...';
          btn.disabled = true;
          
          utterance.onend = () => {{
            btn.innerHTML = originalText;
            btn.disabled = false;
          }};
          
          utterance.onerror = () => {{
            btn.innerHTML = originalText;
            btn.disabled = false;
          }};
          
          window.speechSynthesis.speak(utterance);
        }} else {{
          alert('Text-to-speech is not supported in this browser.');
        }}
      }}

      document.addEventListener('DOMContentLoaded', () => {{
        const episodesPerPage = 5;
        let currentPage = 1;
        const cards = document.querySelectorAll('.episode-card');
        const totalPages = Math.ceil(cards.length / episodesPerPage);
        const controls = document.getElementById('pagination-controls');

        if (cards.length === 0) {{
          if (controls) controls.style.display = 'none';
          return;
        }}

        function showPage(page) {{
          if (page < 1) page = 1;
          if (page > totalPages) page = totalPages;
          currentPage = page;

          const start = (currentPage - 1) * episodesPerPage;
          const end = start + episodesPerPage;

          cards.forEach((card, index) => {{
            if (index >= start && index < end) {{
              card.style.display = 'block';
              card.style.opacity = '0';
              card.style.transition = 'none';
              requestAnimationFrame(() => {{
                card.style.transition = 'opacity 0.4s ease';
                card.style.opacity = '1';
              }});
            }} else {{
              card.style.display = 'none';
            }}
          }});

          document.getElementById('page-info').textContent = `Page ${{currentPage}} of ${{totalPages}}`;
          document.getElementById('prev-btn').disabled = (currentPage === 1);
          document.getElementById('next-btn').disabled = (currentPage === totalPages);
          window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        document.getElementById('prev-btn').addEventListener('click', () => showPage(currentPage - 1));
        document.getElementById('next-btn').addEventListener('click', () => showPage(currentPage + 1));

        showPage(1);
      }});
    </script>
  </body>
</html>"""


def format_rss_table_row(c: Chunk) -> str:
    """Pure formatter that transforms a chunk into an RSS-compliant table row."""
    return f"""            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #334155; font-weight: bold; font-size: 1.1em;">{html.escape(c.get("japanese", ""))}</td>
              <td style="padding: 8px; border-bottom: 1px solid #334155; color: #38bdf8;">{html.escape(c.get("romaji", ""))}</td>
              <td style="padding: 8px; border-bottom: 1px solid #334155;">{html.escape(c.get("meaning", ""))}</td>
            </tr>"""


def format_rss_item(ep: Episode) -> str:
    """Pure formatter that transforms an Episode structure into a compliant RSS XML <item>."""
    chunks_list = ep.get("chunks", [])
    if chunks_list:
        table_rows = "\n".join(format_rss_table_row(c) for c in chunks_list)
        breakdown_html = f"""        <h3>Vocabulary Breakdown:</h3>
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
          <thead>
            <tr style="background-color: #1e293b; color: #f8fafc;">
              <th style="padding: 8px;">Japanese</th>
              <th style="padding: 8px;">Romaji</th>
              <th style="padding: 8px;">English Meaning</th>
            </tr>
          </thead>
          <tbody>
{table_rows}
          </tbody>
        </table>"""
    else:
        breakdown_html = ""

    description_html = f"""        <p><strong>English Title:</strong> <em>{html.escape(ep.get("english_translation", ""))}</em></p>
{breakdown_html}
        <p><a href="{html.escape(ep.get("audio_url", "") or "https://www.radionikkei.jp/nagara/")}">Listen to this Episode on Radio NIKKEI</a></p>"""

    escaped_description = (
        description_html.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

    title_raw = f"{ep.get('japanese_title', '')} - {ep.get('english_translation', '')}"
    escaped_title = html.escape(title_raw)
    escaped_link = html.escape(
        ep.get("audio_url", "") or "https://www.radionikkei.jp/nagara/"
    )
    escaped_guid = html.escape(ep.get("japanese_title", ""))
    escaped_pub_date = html.escape(ep.get("published_at", ""))

    return f"""        <item>
          <title>{escaped_title}</title>
          <link>{escaped_link}</link>
          <guid isPermaLink="false">{escaped_guid}</guid>
          <pubDate>{escaped_pub_date} +0000</pubDate>
          <description>{escaped_description}</description>
        </item>"""


def render_rss_content(items_xml: str) -> str:
    """Pure formatter that builds the complete RSS XML feed envelope."""
    return f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>ながら日経 Vocabulary Tracker</title>
  <link>https://www.radionikkei.jp/nagara/</link>
  <description>Daily Japanese learning chunks, romaji, and translations from the latest Nagara Nikkei podcast titles.</description>
  <language>en-us</language>
{items_xml}
</channel>
</rss>"""


def main() -> None:
    print(
        "Starting PodcastTracker Static Site Generator (Python Typed, Functional & Self-Healing)..."
    )
    os.makedirs(DIST_DIR, exist_ok=True)

    # 1. Load history
    history = load_history()

    # 2. Fetch RSS XML
    print(f"Fetching RSS from {RSS_URL}...")
    try:
        req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
    except Exception as e:
        print(f"Failed to fetch RSS: {e}")
        return

    # 3. Parse XML for first 5 episodes
    episodes_metadata = parse_xml_to_episodes_metadata(xml_data, limit=5)
    if not episodes_metadata:
        print("No metadata parsed from feed.")
        return

    # We will build a set of titles that are processed to log them cleanly
    api_key = get_api_key()
    has_changes = False

    # 4. Self-Healing scan loop
    for title, pub_date_str, audio_url in episodes_metadata:
        parsed_date = parse_date(pub_date_str)

        # Check if the title is already in history and is fully translated
        existing_index = next(
            (i for i, ep in enumerate(history) if ep.get("japanese_title") == title), -1
        )

        needs_translation = (existing_index == -1) or history[existing_index].get(
            "is_mock", False
        )

        if needs_translation:
            print(f"Attempting to translate/heal episode: {title}")
            english, chunks, model_used, is_mock = analyze_japanese(title, api_key)

            new_episode: Episode = {
                "japanese_title": title,
                "english_translation": english,
                "published_at": parsed_date,
                "audio_url": audio_url,
                "chunks": chunks,
                "is_mock": is_mock,
                "translation_model": model_used,
            }

            if existing_index != -1:
                # Heal/replace the existing mock entry
                history[existing_index] = new_episode
                print(
                    f"Successfully healed existing mock episode using {model_used}: {title}"
                )
            else:
                # Prepend new episode
                history.append(new_episode)
                print(f"Added new episode using {model_used}: {title}")

            has_changes = True
        else:
            existing_ep = history[existing_index]
            model_used = existing_ep.get("translation_model", "unknown")
            print(f"Episode already translated (using {model_used}): {title}")

    # 5. Persist database if any additions or heals occurred
    if has_changes:
        save_history(history)
        # Reload history to ensure it is sorted and truncated correctly
        history = load_history()

    # 6. Build static outputs
    print("Generating index.html...")
    cards_html = (
        "\n".join(format_episode_card(ep) for ep in history)
        if history
        else """<div class="empty-state">
  <p>No episodes translated yet. Running the workflow will fetch the latest!</p>
</div>"""
    )
    with open(os.path.join(DIST_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_html_content(cards_html))

    print("Generating rss.xml...")
    items_xml = "\n".join(format_rss_item(ep) for ep in history)
    with open(os.path.join(DIST_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(render_rss_content(items_xml))

    print(f"Static build completed successfully in '{DIST_DIR}' folder!")


if __name__ == "__main__":
    main()
