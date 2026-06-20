import xml.etree.ElementTree as ET
from utils import sanitize_audio_url

# Title prefixes to ignore when parsing RSS items.
# Episodes whose title starts with any of these prefixes are skipped.
IGNORED_TITLE_PREFIXES: tuple[str, ...] = ("NIKKEI THE PITCH",)


def parse_xml_to_episodes_metadata(
    xml_data: bytes, limit: int = 5
) -> list[tuple[str, str, str]]:
    """Pure parser that extracts the first N episodes (title, pubDate, audio_url) from RSS bytes."""
    try:
        # Prevent XML Entity Expansion (Billion Laughs, XXE) by checking for DOCTYPE/ENTITY declarations
        if b"<!DOCTYPE" in xml_data.upper() or b"<!ENTITY" in xml_data.upper():
            raise ValueError("Forbidden DTD or Entity declaration found in XML data")

        root = ET.fromstring(xml_data)
        items = root.findall(".//item")
        metadata_list: list[tuple[str, str, str]] = []
        for item in items:
            if len(metadata_list) >= limit:
                break

            title_elem = item.find("title")
            pub_date_elem = item.find("pubDate")
            link_elem = item.find("link")
            enclosure_elem = item.find("enclosure")

            title = title_elem.text if title_elem is not None else None
            pub_date_str = pub_date_elem.text if pub_date_elem is not None else None

            if not title or not pub_date_str:
                continue

            stripped_title = title.strip()

            # Skip episodes whose title matches an ignored prefix
            if stripped_title.startswith(IGNORED_TITLE_PREFIXES):
                continue

            link = link_elem.text if link_elem is not None else None
            enclosure_url = (
                enclosure_elem.get("url") if enclosure_elem is not None else None
            )

            audio_url = link if link and link.strip() else enclosure_url
            sanitized_audio = sanitize_audio_url(audio_url)

            metadata_list.append(
                (stripped_title, pub_date_str.strip(), sanitized_audio)
            )

        return metadata_list
    except Exception as e:
        print(f"Failed to parse RSS XML: {e}")
    return []
