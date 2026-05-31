#!/usr/bin/env python3
import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
import re
import html

RSS_URL = "https://feeds.megaphone.fm/nagara"
HISTORY_FILE = "history.json"
DIST_DIR = "dist"

def read_from_env_file(key):
    if os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(key + "="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return None

def get_api_key():
    return (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GEMINI_API_TOKEN")
        or read_from_env_file("GEMINI_API_KEY")
        or read_from_env_file("GEMINI_API_TOKEN")
    )

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save history: {e}")

def parse_date(pub_date_str):
    # Format typically: Sun, 31 May 2026 15:30:00 GMT or Sun, 31 May 2026 15:30:00 +0000
    try:
        clean_date_str = re.sub(r'\s+[\+\-]\d{4}$', '', pub_date_str)
        clean_date_str = re.sub(r'\s+GMT$', '', clean_date_str)
        dt = datetime.strptime(clean_date_str.strip(), "%a, %d %b %Y %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def analyze_japanese(title, api_key):
    if not api_key:
        print("GEMINI_API_KEY not set. Using mock translation.")
        return mock_analyze(title)
    
    models = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-3.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite"
    ]
    
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

    for model in models:
        print(f"Attempting translation with model: {model}...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        req_data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        try:
            req = urllib.request.Request(
                url, 
                data=json.dumps(req_data).encode("utf-8"), 
                headers=headers, 
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                text_content = res_body["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_content)
                english = parsed.get("english_translation", "")
                chunks = parsed.get("chunks", [])
                
                if english and chunks:
                    cleaned_chunks = []
                    for c in chunks:
                        cleaned_chunks.append({
                            "japanese": c.get("japanese", ""),
                            "romaji": c.get("romaji", ""),
                            "meaning": c.get("meaning", "")
                        })
                    print(f"Successfully translated using {model}")
                    return english, cleaned_chunks
        except Exception as e:
            print(f"Model {model} failed: {e}")
            continue

    print("All models failed. Using mock.")
    return mock_analyze(title)

def mock_analyze(title):
    mock_english = "Daily Nikkei News: " + title[:11] + "..."
    mock_chunks = [
        {"japanese": "日経", "romaji": "nikkei", "meaning": "Nikkei (newspaper)"},
        {"japanese": "平均", "romaji": "heikin", "meaning": "Average"},
        {"japanese": "は", "romaji": "wa", "meaning": "is (particle)"},
        {"japanese": "反落", "romaji": "hanraku", "meaning": "fell back / declined"}
    ]
    return mock_english, mock_chunks

def generate_html(episodes):
    if not episodes:
        cards_html = """<div class="empty-state">
  <p>No episodes translated yet. Running the workflow will fetch the latest!</p>
</div>"""
    else:
        cards = []
        for ep in episodes:
            chunks_list = []
            for c in ep.get("chunks", []):
                jp_encoded = urllib.parse.quote_plus(c.get("japanese", ""))
                chunk_str = f"""              <div class="chunk">
                <dt>
                  <a href="https://jisho.org/search/{jp_encoded}" target="_blank" rel="noopener noreferrer" class="chunk-jp-link">
                    <span class="chunk-jp">{html.escape(c.get("japanese", ""))}</span>
                  </a>
                  <span class="chunk-ro">{html.escape(c.get("romaji", ""))}</span>
                </dt>
                <dd class="chunk-en">{html.escape(c.get("meaning", ""))}</dd>
              </div>"""
                chunks_list.append(chunk_str)
            chunks_html = "\n".join(chunks_list)
            
            date_formatted = ep.get("published_at", "")[:10]
            audio_url = ep.get("audio_url", "") or "https://www.radionikkei.jp/nagara/"
            
            card_str = f"""          <div class="episode-card">
            <span class="date">{html.escape(date_formatted)}</span>
            <h2 class="japanese-title">
              {html.escape(ep.get("japanese_title", ""))}
              <a href="{html.escape(audio_url)}" target="_blank" rel="noopener noreferrer" class="listen-badge">
                Listen
              </a>
            </h2>
            <p class="english-title">{html.escape(ep.get("english_translation", ""))}</p>

            <dl class="chunks-container">
{chunks_html}
            </dl>
          </div>"""
            cards.append(card_str)
        cards_html = "\n".join(cards)

    html_content = f"""<!DOCTYPE html>
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
      .date {{
        font-size: 0.9rem;
        color: var(--accent);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
        display: block;
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
        transition: background-color 0.2s ease, transform 0.2s ease;
      }}
      .listen-badge:hover {{
        background: var(--accent);
        color: var(--bg-color);
        transform: scale(1.05);
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

    with open(os.path.join(DIST_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

def generate_rss(episodes):
    items = []
    for ep in episodes:
        table_rows = []
        for c in ep.get("chunks", []):
            row = f"""            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #334155; font-weight: bold; font-size: 1.1em;">{html.escape(c.get("japanese", ""))}</td>
              <td style="padding: 8px; border-bottom: 1px solid #334155; color: #38bdf8;">{html.escape(c.get("romaji", ""))}</td>
              <td style="padding: 8px; border-bottom: 1px solid #334155;">{html.escape(c.get("meaning", ""))}</td>
            </tr>"""
            table_rows.append(row)
        table_rows_str = "\n".join(table_rows)

        description_html = f"""        <p><strong>English Title:</strong> <em>{html.escape(ep.get("english_translation", ""))}</em></p>
        <h3>Vocabulary Breakdown:</h3>
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
          <thead>
            <tr style="background-color: #1e293b; color: #f8fafc;">
              <th style="padding: 8px;">Japanese</th>
              <th style="padding: 8px;">Romaji</th>
              <th style="padding: 8px;">English Meaning</th>
            </tr>
          </thead>
          <tbody>
{table_rows_str}
          </tbody>
        </table>
        <p><a href="{html.escape(ep.get("audio_url", "") or "https://www.radionikkei.jp/nagara/")}">Listen to this Episode on Radio NIKKEI</a></p>"""

        # Escape HTML for XML compliance
        escaped_description = (
            description_html
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

        title_raw = f"{ep.get('japanese_title', '')} - {ep.get('english_translation', '')}"
        escaped_title = html.escape(title_raw)
        escaped_link = html.escape(ep.get("audio_url", "") or "https://www.radionikkei.jp/nagara/")
        escaped_guid = html.escape(ep.get("japanese_title", ""))
        escaped_pub_date = html.escape(ep.get("published_at", ""))

        item = f"""        <item>
          <title>{escaped_title}</title>
          <link>{escaped_link}</link>
          <guid isPermaLink="false">{escaped_guid}</guid>
          <pubDate>{escaped_pub_date} +0000</pubDate>
          <description>{escaped_description}</description>
        </item>"""
        items.append(item)

    items_xml = "\n".join(items)

    rss_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>ながら日経 Vocabulary Tracker</title>
  <link>https://www.radionikkei.jp/nagara/</link>
  <description>Daily Japanese learning chunks, romaji, and translations from the latest Nagara Nikkei podcast titles.</description>
  <language>en-us</language>
{items_xml}
</channel>
</rss>"""

    with open(os.path.join(DIST_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_content)

def main():
    print("Starting PodcastTracker Static Site Generator (Python Native)...")
    os.makedirs(DIST_DIR, exist_ok=True)
    
    # 1. Load history
    history = load_history()
    
    # 2. Fetch RSS
    print(f"Fetching RSS from {RSS_URL}...")
    try:
        req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
    except Exception as e:
        print(f"Failed to fetch RSS: {e}")
        return

    # 3. Parse XML
    try:
        root = ET.fromstring(xml_data)
        item = root.find(".//item")
        if item is None:
            print("No items found in RSS feed.")
            return
            
        title = item.find("title").text if item.find("title") is not None else None
        pub_date_str = item.find("pubDate").text if item.find("pubDate") is not None else None
        
        # Link & audio
        link_elem = item.find("link")
        link = link_elem.text if link_elem is not None else None
        
        enclosure = item.find("enclosure")
        enclosure_url = enclosure.get("url") if enclosure is not None else None
        
        audio_url = link if link and link.strip() else enclosure_url
    except Exception as e:
        print(f"Failed to parse RSS XML: {e}")
        return

    if not title or not title.strip():
        print("Empty or missing title in RSS feed.")
        return

    parsed_date = parse_date(pub_date_str)
    
    # 4. Check if episode already exists
    existing = [ep for ep in history if ep.get("japanese_title") == title]
    
    if not existing:
        print(f"Found new episode: {title}")
        api_key = get_api_key()
        english, chunks = analyze_japanese(title, api_key)
        
        new_episode = {
            "japanese_title": title,
            "english_translation": english,
            "published_at": parsed_date,
            "audio_url": audio_url,
            "chunks": chunks
        }
        
        # Prepend and limit to latest 100 items
        history = [new_episode] + history
        history = history[:100]
        
        # Save updated history
        save_history(history)
    else:
        print("Episode already exists in history.")

    # 5. Generate Outputs
    print("Generating index.html...")
    generate_html(history)
    
    print("Generating rss.xml...")
    generate_rss(history)
    
    print(f"Static build completed successfully in '{DIST_DIR}' folder!")

if __name__ == "__main__":
    main()
