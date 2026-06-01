#!/usr/bin/env python3
import os
import unittest
import difflib
import sys
from typing import Callable

# Import our builder functions
from build import (
    parse_date,
    parse_xml_to_episodes_metadata,
    format_chunk_html,
    format_episode_card,
    render_html_content,
    render_rss_content,
    format_rss_item,
    clean_json_text,
    Chunk,
    Episode,
    History,
    BASE_URL,
)


EXPECT_DIR = "test/expect"
UPDATE_EXPECT = os.environ.get("UPDATE_EXPECT") == "1"


class TestBuild(unittest.TestCase):
    def setUp(self) -> None:
        os.makedirs(EXPECT_DIR, exist_ok=True)

        # Consistent mock history for deterministic snapshot generation
        self.mock_history: History = [
            {
                "japanese_title": "日経平均は反落、米ハイテク安で売り優勢",
                "english_translation": "Nikkei average falls back, selling dominant due to US tech decline",
                "published_at": "2026-05-31 15:30:00",
                "audio_url": "https://feeds.megaphone.fm/nagara-sample",
                "chunks": [
                    {
                        "japanese": "日経平均",
                        "romaji": "nikkei heikin",
                        "meaning": "Nikkei average",
                    },
                    {"japanese": "は", "romaji": "wa", "meaning": "is (particle)"},
                    {
                        "japanese": "反落",
                        "romaji": "hanraku",
                        "meaning": "fell back / declined",
                    },
                ],
                "is_mock": False,
            }
        ]

    def assert_expect(self, filename: str, actual: str) -> None:
        """Helper that compares actual output with expected golden file.

        If UPDATE_EXPECT=1 is set, it automatically updates the golden file.
        """
        filepath = os.path.join(EXPECT_DIR, filename)

        if UPDATE_EXPECT:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(actual)
            print(f"Updated expectation: {filepath}")
            return

        if not os.path.exists(filepath):
            # If golden file doesn't exist, create it on first run
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(actual)
            print(f"Created expectation: {filepath}")
            return

        with open(filepath, "r", encoding="utf-8") as f:
            expected = f.read()

        if actual != expected:
            # Generate a beautiful git-style unified diff
            diff = difflib.unified_diff(
                expected.splitlines(keepends=True),
                actual.splitlines(keepends=True),
                fromfile=f"Expected ({filename})",
                tofile="Actual Output",
            )
            diff_text = "".join(diff)
            self.fail(
                f"Expectation mismatch in {filename}!\n"
                f"To update this expectation, run: UPDATE_EXPECT=1 python test_build.py\n\n"
                f"{diff_text}"
            )

    # 1. Unit Tests for pure functions
    def test_parse_date(self) -> None:
        self.assertEqual(
            parse_date("Sun, 31 May 2026 15:30:00 GMT"), "2026-06-01 00:30:00"
        )
        self.assertEqual(
            parse_date("Sun, 31 May 2026 15:30:00 +0000"), "2026-06-01 00:30:00"
        )

    def test_parse_xml_to_episodes_metadata(self) -> None:
        xml_bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss>
          <channel>
            <item>
              <title>Sample Episode Title</title>
              <pubDate>Sun, 31 May 2026 15:30:00 GMT</pubDate>
              <link>https://www.radionikkei.jp/nagara/sample.html</link>
            </item>
          </channel>
        </rss>"""
        episodes = parse_xml_to_episodes_metadata(xml_bytes, limit=1)
        self.assertEqual(len(episodes), 1)
        title, pub_date, audio_url = episodes[0]
        self.assertEqual(title, "Sample Episode Title")
        self.assertEqual(pub_date, "Sun, 31 May 2026 15:30:00 GMT")
        self.assertEqual(audio_url, "https://www.radionikkei.jp/nagara/sample.html")

    def test_clean_json_text(self) -> None:
        raw_markdown = '```json\n{"english_translation": "Test", "chunks": []}\n```'
        raw_markdown_no_lang = '```\n{"english_translation": "Test", "chunks": []}\n```'
        clean_json = '{"english_translation": "Test", "chunks": []}'

        self.assertEqual(clean_json_text(raw_markdown).strip(), clean_json)
        self.assertEqual(clean_json_text(raw_markdown_no_lang).strip(), clean_json)
        self.assertEqual(clean_json_text(clean_json).strip(), clean_json)

    # 2. Expect (Snapshot) Tests for HTML & XML generation
    def test_expect_chunk_html(self) -> None:
        chunk: Chunk = {
            "japanese": "反落",
            "romaji": "hanraku",
            "meaning": "fell back / declined",
        }
        actual_html = format_chunk_html(chunk)
        self.assert_expect("chunk.html", actual_html)

    def test_expect_episode_card(self) -> None:
        actual_html = format_episode_card(self.mock_history[0])
        self.assert_expect("episode_card.html", actual_html)

    def test_expect_full_html_page(self) -> None:
        cards_html = "\n".join(format_episode_card(ep) for ep in self.mock_history)
        actual_html = render_html_content(cards_html)
        self.assert_expect("index.html", actual_html)

    def test_expect_individual_html_page(self) -> None:
        ep = self.mock_history[0]
        back_link_html = """            <div class="back-link-container">
              <a href="index.html" class="back-link">← Back to Dashboard</a>
            </div>"""
        card_html = format_episode_card(ep)
        jp_title = ep.get("japanese_title", "")
        en_trans = ep.get("english_translation", "")
        page_title = f"ながら日経 Tracker • {jp_title}"
        page_desc = f"English Translation: {en_trans}"
        og_page_url = f"{BASE_URL}/2026-05-31.html"

        actual_html = render_html_content(
            f"{back_link_html}\n{card_html}",
            title=page_title,
            description=page_desc,
            og_url=og_page_url,
        )
        self.assert_expect("episode_page.html", actual_html)

    def test_expect_rss_item(self) -> None:
        actual_xml = format_rss_item(self.mock_history[0])
        self.assert_expect("rss_item.xml", actual_xml)

    def test_expect_full_rss_feed(self) -> None:
        items_xml = "\n".join(format_rss_item(ep) for ep in self.mock_history)
        actual_xml = render_rss_content(items_xml)
        self.assert_expect("rss.xml", actual_xml)

    def test_malicious_audio_url_sanitization(self) -> None:
        malicious_episode: Episode = {
            "japanese_title": "テスト",
            "english_translation": "Test",
            "published_at": "2026-05-31 15:30:00",
            "audio_url": "javascript:alert('xss')",
            "chunks": [],
            "is_mock": False,
        }
        card_html = format_episode_card(malicious_episode)
        rss_item_xml = format_rss_item(malicious_episode)

        # Verify both formats fall back to a safe URL and do not contain javascript:
        self.assertNotIn("javascript:alert('xss')", card_html)
        self.assertNotIn("javascript:alert('xss')", rss_item_xml)
        self.assertIn("https://www.radionikkei.jp/nagara/", card_html)
        self.assertIn("https://www.radionikkei.jp/nagara/", rss_item_xml)


if __name__ == "__main__":
    unittest.main()
