#!/usr/bin/env python3
import os
import urllib.request
from dataclasses import replace
from typing import assert_never

# 1. Backwards-compatible imports and re-exposures
from models import (
    Chunk,
    Episode,
    History,
    BASE_URL,
    DIST_DIR,
    RSS_URL,
    JapaneseText,
    EnglishText,
    JSTDateTime,
    AudioURL,
    TranslationSuccess,
    TranslationFailure,
)
from utils import (
    parse_date,
    clean_json_text,
    sanitize_audio_url,
    get_api_key,
    read_from_env_file,
)
from history import load_history, save_history
from parser import parse_xml_to_episodes_metadata
from analyzer import analyze_japanese, mock_analyze, try_models_recursively
from templates import format_chunk_html, format_episode_card, render_html_content
from rss_generator import format_rss_item, render_rss_content, format_rss_table_row

__all__ = [
    "Chunk",
    "Episode",
    "History",
    "BASE_URL",
    "DIST_DIR",
    "RSS_URL",
    "parse_date",
    "clean_json_text",
    "sanitize_audio_url",
    "get_api_key",
    "read_from_env_file",
    "load_history",
    "save_history",
    "parse_xml_to_episodes_metadata",
    "analyze_japanese",
    "mock_analyze",
    "try_models_recursively",
    "format_chunk_html",
    "format_episode_card",
    "render_html_content",
    "format_rss_item",
    "render_rss_content",
    "format_rss_table_row",
    "main",
]


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
            (i for i, ep in enumerate(history) if ep.japanese_title == title), -1
        )

        needs_translation = (existing_index == -1) or history[existing_index].is_mock

        if needs_translation:
            print(f"Attempting to translate/heal episode: {title}")
            res = analyze_japanese(JapaneseText(title), api_key)

            match res:
                case TranslationSuccess(english, chunks, model_used):
                    new_episode = Episode(
                        japanese_title=JapaneseText(title),
                        english_translation=english,
                        published_at=JSTDateTime(parsed_date),
                        audio_url=AudioURL(audio_url),
                        chunks=chunks,
                        is_mock=False,
                        translation_model=model_used,
                    )
                case TranslationFailure(english, chunks, model_used):
                    new_episode = Episode(
                        japanese_title=JapaneseText(title),
                        english_translation=english,
                        published_at=JSTDateTime(parsed_date),
                        audio_url=AudioURL(audio_url),
                        chunks=chunks,
                        is_mock=True,
                        translation_model=model_used,
                    )
                case unreachable:
                    assert_never(unreachable)

            if existing_index != -1:
                # Heal/replace the existing mock entry
                history[existing_index] = new_episode
                print(
                    f"Successfully healed existing mock episode using {new_episode.translation_model}: {title}"
                )
            else:
                # Prepend new episode
                history.append(new_episode)
                print(
                    f"Added new episode using {new_episode.translation_model}: {title}"
                )

            has_changes = True
        else:
            existing_ep = history[existing_index]
            model_used = existing_ep.translation_model
            # Self-heal metadata timezones or audio URLs if generator configurations updated
            if (
                existing_ep.published_at != parsed_date
                or existing_ep.audio_url != audio_url
            ):
                history[existing_index] = replace(
                    existing_ep,
                    published_at=JSTDateTime(parsed_date),
                    audio_url=AudioURL(audio_url),
                )
                has_changes = True
                print(f"Self-healed timezone/metadata for: {title} -> {parsed_date}")
            else:
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
        f.write(
            render_html_content(
                cards_html,
                title="ながら日経 Podcast Tracker",
                description="Daily Japanese learning chunks, romaji, and translations from the latest Nagara Nikkei podcast titles.",
                og_url=f"{BASE_URL}/",
            )
        )

    print("Generating individual episode pages...")
    for ep in history:
        date_formatted = ep.published_at[:10]
        if date_formatted:
            back_link_html = """            <div class="back-link-container">
              <a href="index.html" class="back-link">← Back to Dashboard</a>
            </div>"""
            card_html = format_episode_card(ep)

            # Dynamic social media preview metadata (Telegram, Discord, Twitter/X, etc.)
            jp_title = ep.japanese_title
            en_trans = ep.english_translation
            page_title = f"ながら日経 Tracker • {jp_title}"
            page_desc = f"English Translation: {en_trans}"
            og_page_url = f"{BASE_URL}/{date_formatted}.html"

            single_page_content = render_html_content(
                f"{back_link_html}\n{card_html}",
                title=page_title,
                description=page_desc,
                og_url=og_page_url,
            )
            page_path = os.path.join(DIST_DIR, f"{date_formatted}.html")
            with open(page_path, "w", encoding="utf-8") as f:
                f.write(single_page_content)

    print("Generating rss.xml...")
    items_xml = "\n".join(format_rss_item(ep) for ep in history)
    with open(os.path.join(DIST_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(render_rss_content(items_xml))

    print("Generating learning-words.html...")
    learning_words_html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>My Learning Words - Tracker</title>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

      :root {{
        --bg-color: #0f172a;
        --card-bg: #1e293b;
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        --accent: #38bdf8;
        --border-color: #334155;
        --accent-glow: rgba(56, 189, 248, 0.1);
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
      .top-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 40px;
        padding-bottom: 20px;
        border-bottom: 1px solid var(--border-color);
      }}
      .back-btn {{
        color: var(--accent);
        text-decoration: none;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: transform 0.2s ease;
      }}
      .back-btn:hover {{
        transform: translateX(-4px);
      }}
      h1 {{
        font-size: 2.2rem;
        margin: 0 0 10px 0;
        background: linear-gradient(135deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
      }}
      p.subtitle {{
        color: var(--text-muted);
        margin: 0 0 30px 0;
      }}
      .view-selector {{
        display: flex;
        gap: 15px;
        margin-bottom: 30px;
      }}
      .view-btn {{
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        color: var(--text-main);
        padding: 10px 20px;
        border-radius: 8px;
        cursor: pointer;
        font-family: inherit;
        font-weight: 600;
        transition: background-color 0.2s ease, border-color 0.2s ease;
      }}
      .view-btn.active {{
        border-color: var(--accent);
        background: var(--accent-glow);
        color: var(--accent);
      }}
      .word-list-container, .flashcard-container {{
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
      }}
      .empty-state {{
        text-align: center;
        padding: 50px 20px;
        color: var(--text-muted);
      }}
      .vocab-table {{
        width: 100%;
        border-collapse: collapse;
        text-align: left;
      }}
      .vocab-table th, .vocab-table td {{
        padding: 14px 16px;
        border-bottom: 1px solid var(--border-color);
      }}
      .vocab-table th {{
        color: var(--text-muted);
        font-weight: 600;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }}
      .vocab-table tr:last-child td {{
        border-bottom: none;
      }}
      .jp-word {{
        font-size: 1.15rem;
        font-weight: 600;
      }}
      .ro-word {{
        color: var(--accent);
        font-size: 0.9rem;
      }}
      .source-link {{
        font-size: 0.8rem;
        color: var(--accent);
        text-decoration: none;
        background: var(--accent-glow);
        padding: 4px 8px;
        border-radius: 4px;
        max-width: 150px;
        display: inline-block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }}
      .source-link:hover {{
        text-decoration: underline;
      }}
      .delete-btn {{
        background: transparent;
        border: none;
        color: #ef4444;
        cursor: pointer;
        font-size: 1.1rem;
        padding: 4px;
        border-radius: 4px;
        transition: background-color 0.2s ease;
      }}
      .delete-btn:hover {{
        background-color: rgba(239, 68, 68, 0.1);
      }}
      .flashcard-widget {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 250px;
        text-align: center;
        padding: 20px;
      }}
      .card-face {{
        font-size: 2.5rem;
        font-weight: 600;
        margin-bottom: 20px;
      }}
      .card-detail {{
        margin-bottom: 30px;
        min-height: 80px;
      }}
      .card-ro {{
        font-size: 1.1rem;
        color: var(--accent);
        margin-bottom: 8px;
      }}
      .card-en {{
        font-size: 1.3rem;
        color: var(--text-main);
      }}
      .reveal-btn {{
        background: var(--accent);
        border: none;
        color: var(--bg-color);
        padding: 12px 30px;
        font-weight: 600;
        border-radius: 8px;
        cursor: pointer;
        font-family: inherit;
        transition: transform 0.2s ease, opacity 0.2s ease;
      }}
      .reveal-btn:hover {{
        transform: scale(1.05);
      }}
      .flashcard-nav {{
        display: flex;
        gap: 20px;
        margin-top: 20px;
      }}
      .nav-btn {{
        background: transparent;
        border: 1px solid var(--border-color);
        color: var(--text-main);
        padding: 8px 20px;
        border-radius: 6px;
        cursor: pointer;
        font-family: inherit;
        font-weight: 600;
        transition: border-color 0.2s ease, color 0.2s ease;
      }}
      .nav-btn:hover:not(:disabled) {{
        border-color: var(--accent);
        color: var(--accent);
      }}
      .nav-btn:disabled {{
        opacity: 0.5;
        cursor: not-allowed;
      }}
      .keyboard-legend {{
        margin-top: 25px;
        font-size: 0.85rem;
        color: var(--text-muted);
        opacity: 0.85;
        border-top: 1px solid var(--border-color);
        padding-top: 15px;
        width: 100%;
        text-align: center;
      }}
      .keyboard-legend code {{
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 2px 6px;
        font-family: monospace;
        color: var(--accent);
      }}
    </style>
  </head>
  <body>
    <div class="container">
      <div class="top-bar">
        <a href="index.html" class="back-btn">← Back to Tracker</a>
      </div>

      <h1>My Saved Vocabulary</h1>
      <p class="subtitle">Review and practice your saved words using list and flashcard mode.</p>

      <div class="view-selector">
        <button id="list-view-btn" class="view-btn active" onclick="switchView('list')">📋 List View</button>
        <button id="flash-view-btn" class="view-btn" onclick="switchView('flash')">🎴 Flashcard Mode</button>
      </div>

      <div id="list-view" class="word-list-container">
        <!-- Dynamically populated -->
      </div>

      <div id="flash-view" class="flashcard-container" style="display: none;">
        <!-- Dynamically populated -->
      </div>
    </div>

    <script>
      let savedWords = [];
      let currentCardIndex = 0;
      let isRevealed = false;

      function loadSavedWords() {{
        savedWords = JSON.parse(localStorage.getItem('learning_words') || '[]');
        renderListView();
        renderFlashcardView();
      }}

      function switchView(view) {{
        const listBtn = document.getElementById('list-view-btn');
        const flashBtn = document.getElementById('flash-view-btn');
        const listView = document.getElementById('list-view');
        const flashView = document.getElementById('flash-view');

        if (view === 'list') {{
          listBtn.classList.add('active');
          flashBtn.classList.remove('active');
          listView.style.display = 'block';
          flashView.style.display = 'none';
        }} else {{
          listBtn.classList.remove('active');
          flashBtn.classList.add('active');
          listView.style.display = 'none';
          flashView.style.display = 'block';
          currentCardIndex = 0;
          isRevealed = false;
          renderFlashcardView();
        }}
      }}

      function deleteWord(btn) {{
        const jp = btn.getAttribute('data-jp');
        savedWords = savedWords.filter(w => w.japanese !== jp);
        localStorage.setItem('learning_words', JSON.stringify(savedWords));
        renderListView();
        if (document.getElementById('flash-view').style.display !== 'none') {{
          currentCardIndex = Math.max(0, Math.min(currentCardIndex, savedWords.length - 1));
          isRevealed = false;
          renderFlashcardView();
        }}
      }}

      function renderListView() {{
        const container = document.getElementById('list-view');
        if (savedWords.length === 0) {{
          container.innerHTML = `
            <div class="empty-state">
              <h3>No words saved yet!</h3>
              <p>Go back to the dashboard and click the star ☆ icon next to any vocabulary word to add it here.</p>
            </div>
          `;
          return;
        }}

        let rowsHtml = savedWords.map(w => `
          <tr>
            <td>
              <div class="jp-word">${{escapeHtml(w.japanese)}}</div>
              <div class="ro-word">${{escapeHtml(w.romaji)}}</div>
            </td>
            <td>${{escapeHtml(w.meaning)}}</td>
            <td>
              <a href="${{escapeHtml(w.post_url)}}" class="source-link" title="${{escapeHtml(w.post_title)}}">
                🔗 ${{escapeHtml(w.post_title)}}
              </a>
            </td>
            <td style="text-align: right;">
              <button class="delete-btn" onclick="deleteWord(this)" data-jp="${{escapeHtml(w.japanese)}}">🗑️</button>
            </td>
          </tr>
        `).join('');

        container.innerHTML = `
          <table class="vocab-table">
            <thead>
              <tr>
                <th style="width: 30%;">Word</th>
                <th style="width: 35%;">Meaning</th>
                <th style="width: 25%;">Source Post</th>
                <th style="width: 10%; text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody>
              ${{rowsHtml}}
            </tbody>
          </table>
        `;
      }}

      function renderFlashcardView() {{
        const container = document.getElementById('flash-view');
        if (savedWords.length === 0) {{
          container.innerHTML = `
            <div class="empty-state">
              <h3>No flashcards available</h3>
              <p>Add some vocabulary words from the tracker homepage first!</p>
            </div>
          `;
          return;
        }}

        const word = savedWords[currentCardIndex];
        const detailHtml = isRevealed ? `
          <div class="card-ro">${{escapeHtml(word.romaji)}}</div>
          <div class="card-en">${{escapeHtml(word.meaning)}}</div>
        ` : `
          <button class="reveal-btn" onclick="revealCard()">Reveal Meaning</button>
        `;

        container.innerHTML = `
          <div class="flashcard-widget">
            <div class="card-face">${{escapeHtml(word.japanese)}}</div>
            <div class="card-detail">
              ${{detailHtml}}
            </div>
            
            <div class="flashcard-nav">
              <button class="nav-btn" onclick="prevCard()" ${{currentCardIndex === 0 ? 'disabled' : ''}}>Previous</button>
              <span style="align-self: center; color: var(--text-muted); font-size: 0.9rem;">
                Card ${{currentCardIndex + 1}} of ${{savedWords.length}}
              </span>
              <button class="nav-btn" onclick="nextCard()" ${{currentCardIndex === savedWords.length - 1 ? 'disabled' : ''}}>Next</button>
            </div>
            
            <div class="keyboard-legend">
              💡 <strong>Keyboard Shortcuts:</strong> Press <code>Space</code> to Reveal/Next • <code>←</code> / <code>→</code> Arrow keys for Prev/Next
            </div>
          </div>
        `;
      }}

      function revealCard() {{
        isRevealed = true;
        renderFlashcardView();
      }}

      function nextCard() {{
        if (currentCardIndex < savedWords.length - 1) {{
          currentCardIndex++;
          isRevealed = false;
          renderFlashcardView();
        }}
      }}

      function prevCard() {{
        if (currentCardIndex > 0) {{
          currentCardIndex--;
          isRevealed = false;
          renderFlashcardView();
        }}
      }}

      function escapeHtml(str) {{
        return str
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#039;");
      }}

      document.addEventListener('keydown', (e) => {{
        // Only active if flash view is visible and we have words
        const flashView = document.getElementById('flash-view');
        if (!flashView || flashView.style.display === 'none' || savedWords.length === 0) {{
          return;
        }}

        switch (e.key) {{
          case ' ':
            // Prevent scrolling on spacebar press
            e.preventDefault();
            if (!isRevealed) {{
              revealCard();
            }} else {{
              nextCard();
            }}
            break;
          case 'ArrowLeft':
            prevCard();
            break;
          case 'ArrowRight':
            nextCard();
            break;
          case 'Enter':
            if (!isRevealed) {{
              revealCard();
            }}
            break;
        }}
      }});

      document.addEventListener('DOMContentLoaded', loadSavedWords);
    </script>
  </body>
</html>"""
    with open(
        os.path.join(DIST_DIR, "learning-words.html"), "w", encoding="utf-8"
    ) as f:
        f.write(learning_words_html)

    print(f"Static build completed successfully in '{DIST_DIR}' folder!")


if __name__ == "__main__":
    main()
