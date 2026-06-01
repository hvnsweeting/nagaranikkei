import urllib.parse
import html
from models import Chunk, Episode
from utils import sanitize_audio_url


def format_chunk_html(c: Chunk, slug: str, ep_title: str) -> str:
    """Pure formatter that transforms a vocabulary chunk to HTML list items with save buttons."""
    jp_encoded = urllib.parse.quote_plus(c.get("japanese", ""))
    jp = c.get("japanese", "")
    ro = c.get("romaji", "")
    en = c.get("meaning", "")

    # HTML attributes escaping
    escaped_jp = html.escape(jp)
    escaped_ro = html.escape(ro)
    escaped_en = html.escape(en)
    escaped_slug = html.escape(slug)
    escaped_ep_title = html.escape(ep_title)

    return f"""              <div class="chunk">
                <dt>
                  <a href="https://jisho.org/search/{jp_encoded}" target="_blank" rel="noopener noreferrer" class="chunk-jp-link">
                    <span class="chunk-jp">{escaped_jp}</span>
                  </a>
                  <span class="chunk-ro">{escaped_ro}</span>
                </dt>
                <dd class="chunk-en">{escaped_en}</dd>
                <div>
                  <button class="save-word-btn" onclick="toggleSaveWord(this)" data-jp="{escaped_jp}" data-ro="{escaped_ro}" data-en="{escaped_en}" data-url="{escaped_slug}.html" data-title="{escaped_ep_title}" title="Save to learning list" aria-label="Save to learning list">
                    ☆
                  </button>
                </div>
              </div>"""


def format_episode_card(ep: Episode) -> str:
    """Pure formatter that transforms an Episode card structure to beautiful dynamic HTML."""
    date_formatted = ep.get("published_at", "")[:10]
    ep_title = ep.get("japanese_title", "")

    chunks_list = ep.get("chunks", [])
    chunks_html = ""
    if chunks_list:
        chunks_html = "\n".join(
            format_chunk_html(c, date_formatted, ep_title) for c in chunks_list
        )
        chunks_container = f"""            <dl class="chunks-container collapsed">
{chunks_html}
            </dl>"""
    else:
        chunks_container = ""

    audio_url = sanitize_audio_url(ep.get("audio_url", ""))

    is_mock = ep.get("is_mock", False)
    title_class = "english-title translation-pending" if is_mock else "english-title"

    num_chunks = len(chunks_list)
    toggle_btn = ""
    if num_chunks > 0:
        toggle_btn = f"""            <button onclick="toggleChunks(this)" data-count="{num_chunks}" class="toggle-chunks-btn" aria-expanded="false">
              📖 Show Vocabulary Chunks ({num_chunks})
            </button>"""

    return f"""          <div class="episode-card">
            <div class="card-meta">
              <span class="date">{html.escape(date_formatted)}</span>
              <a href="{html.escape(audio_url)}" target="_blank" rel="noopener noreferrer" class="podcast-link">
                Podcast Link
              </a>
              <span class="meta-divider">•</span>
              <a href="{html.escape(date_formatted)}.html" class="permalink">
                Permalink
              </a>
            </div>
            <h2 class="japanese-title">
              {html.escape(ep.get("japanese_title", ""))}
              <button onclick="speakTitle(this)" data-title="{html.escape(ep.get("japanese_title", ""))}" class="listen-badge" title="Read title aloud">
                🔊
              </button>
            </h2>
            <p class="{title_class}">{html.escape(ep.get("english_translation", ""))}</p>
{toggle_btn}
{chunks_container}
          </div>"""


def render_html_content(
    cards_html: str,
    title: str = "ながら日経 Podcast Tracker",
    description: str = "Daily Japanese learning chunks, romaji, and translations from the latest Nagara Nikkei podcast titles.",
    og_url: str = "https://hvnsweeting.github.io/nagaranikkei/",
) -> str:
    """Pure formatter that produces the full-page static index.html dashboard template."""
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(title)}</title>
    <meta name="description" content="{html.escape(description)}" />

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website" />
    <meta property="og:url" content="{html.escape(og_url)}" />
    <meta property="og:title" content="{html.escape(title)}" />
    <meta property="og:description" content="{html.escape(description)}" />

    <!-- Twitter -->
    <meta property="twitter:card" content="summary" />
    <meta property="twitter:url" content="{html.escape(og_url)}" />
    <meta property="twitter:title" content="{html.escape(title)}" />
    <meta property="twitter:description" content="{html.escape(description)}" />
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
      .top-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 40px;
        padding-bottom: 20px;
        border-bottom: 1px solid var(--border-color);
      }}
      .logo-link {{
        text-decoration: none;
        color: var(--text-main);
        font-weight: 600;
        font-size: 1.2rem;
        transition: color 0.2s ease;
      }}
      .logo-link:hover {{
        color: var(--accent);
      }}
      .saved-words-btn {{
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        color: var(--text-main);
        font-size: 0.9rem;
        padding: 8px 16px;
        border-radius: 8px;
        cursor: pointer;
        text-decoration: none;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        transition: background-color 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
      }}
      .saved-words-btn:hover {{
        background: rgba(255, 255, 255, 0.05);
        border-color: var(--accent);
        transform: scale(1.02);
      }}
      .saved-words-btn .badge {{
        background: var(--accent);
        color: var(--bg-color);
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 9999px;
        font-weight: bold;
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
      .meta-divider {{
        color: var(--text-muted);
        opacity: 0.5;
        font-size: 0.85rem;
      }}
      .permalink {{
        font-size: 0.85rem;
        color: var(--text-muted);
        text-decoration: none;
        transition: color 0.2s ease;
      }}
      .permalink:hover {{
        color: var(--accent);
        text-decoration: underline;
      }}
      .back-link-container {{
        margin-bottom: 30px;
      }}
      .back-link {{
        color: var(--accent);
        text-decoration: none;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: transform 0.2s ease;
      }}
      .back-link:hover {{
        transform: translateX(-4px);
        text-decoration: underline;
      }}
      .toggle-chunks-btn {{
        background: transparent;
        border: 1px solid var(--border-color);
        color: var(--text-muted);
        font-size: 0.85rem;
        padding: 6px 16px;
        border-radius: 8px;
        cursor: pointer;
        font-family: inherit;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
        margin-top: 10px;
      }}
      .toggle-chunks-btn:hover {{
        background: rgba(255, 255, 255, 0.03);
        border-color: var(--accent);
        color: var(--accent);
      }}
      .chunks-container.collapsed {{
        display: none;
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
        grid-template-columns: 220px 1fr auto;
        align-items: center;
        gap: 20px;
        padding: 16px 20px;
        border-bottom: 1px solid var(--border-color);
        margin: 0;
        transition: background-color 0.2s ease;
        cursor: default;
      }}
      .save-word-btn {{
        background: transparent;
        border: none;
        color: var(--text-muted);
        cursor: pointer;
        font-size: 1.25rem;
        padding: 4px;
        transition: color 0.2s ease, transform 0.2s ease;
        line-height: 1;
      }}
      .save-word-btn:hover {{
        color: #eab308;
        transform: scale(1.2);
      }}
      .save-word-btn.saved {{
        color: #eab308;
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
      <div class="top-bar">
        <a href="index.html" class="logo-link">
          ながら日経 Tracker
        </a>
        <a href="learning-words.html" class="saved-words-btn">
          ⭐ Saved Words <span class="badge" id="saved-words-count">0</span>
        </a>
      </div>

      <header style="text-align: center; margin-bottom: 50px;">
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

      function toggleChunks(btn) {{
        const card = btn.closest('.episode-card');
        const container = card.querySelector('.chunks-container');
        if (container) {{
          const isCollapsed = container.classList.toggle('collapsed');
          btn.setAttribute('aria-expanded', !isCollapsed);
          const count = btn.getAttribute('data-count');
          btn.innerHTML = isCollapsed ? `📖 Show Vocabulary Chunks (${{count}})` : `📘 Hide Vocabulary Chunks`;
        }}
      }}

      function toggleSaveWord(btn) {{
        const jp = btn.getAttribute('data-jp');
        const ro = btn.getAttribute('data-ro');
        const en = btn.getAttribute('data-en');
        const url = btn.getAttribute('data-url');
        const title = btn.getAttribute('data-title');
        
        let saved = JSON.parse(localStorage.getItem('learning_words') || '[]');
        const index = saved.findIndex(item => item.japanese === jp);
        
        if (index > -1) {{
          saved.splice(index, 1);
          btn.classList.remove('saved');
          btn.innerHTML = '☆';
          btn.title = 'Save to learning list';
        }} else {{
          saved.push({{
            japanese: jp,
            romaji: ro,
            meaning: en,
            post_url: url,
            post_title: title,
            saved_at: new Date().toISOString()
          }});
          btn.classList.add('saved');
          btn.innerHTML = '★';
          btn.title = 'Saved';
        }}
        
        localStorage.setItem('learning_words', JSON.stringify(saved));
        syncSavedWordButtons();
      }}

      function syncSavedWordButtons() {{
        const saved = JSON.parse(localStorage.getItem('learning_words') || '[]');
        const savedJps = new Set(saved.map(item => item.japanese));
        
        document.querySelectorAll('.save-word-btn').forEach(btn => {{
          const jp = btn.getAttribute('data-jp');
          if (savedJps.has(jp)) {{
            btn.classList.add('saved');
            btn.innerHTML = '★';
            btn.title = 'Saved';
          }} else {{
            btn.classList.remove('saved');
            btn.innerHTML = '☆';
            btn.title = 'Save to learning list';
          }}
        }});
        
        const badge = document.getElementById('saved-words-count');
        if (badge) {{
          badge.textContent = saved.length;
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
        syncSavedWordButtons();
      }});
    </script>
  </body>
</html>"""
