import html
from models import Chunk, Episode, BASE_URL
from utils import sanitize_audio_url


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

    date_formatted = ep.get("published_at", "")[:10]
    site_url = f"{BASE_URL}/{date_formatted}.html" if date_formatted else BASE_URL
    audio_url = sanitize_audio_url(ep.get("audio_url", ""))

    description_html = f"""        <p><strong>English Title:</strong> <em>{html.escape(ep.get("english_translation", ""))}</em></p>
{breakdown_html}
        <p><a href="{html.escape(site_url)}">View Translation &amp; Vocabulary Breakdown on Tracker</a></p>
        <p><a href="{html.escape(audio_url)}">Play Audio (Media Link)</a></p>"""

    escaped_description = (
        description_html.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

    title_raw = f"{ep.get('japanese_title', '')} - {ep.get('english_translation', '')}"
    escaped_title = html.escape(title_raw)
    escaped_link = html.escape(site_url)
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
