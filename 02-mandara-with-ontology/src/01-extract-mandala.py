"""
Extracts Level-1 and Level-2 taxonomy terms from the Failure Mandala (mandara.html).

Outputs a JSON file with the three Mandala dimensions:
  - 原因 (Cause)  → CauseType
  - 行動 (Action) → ActionType
  - 結果 (Result) → ResultType
"""

import json
import logging
import os

from bs4 import BeautifulSoup, Tag

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

SCRIPT_DIR = os.path.realpath(__file__)
PRJ_DIR    = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
BLD_DIR    = os.path.join(PRJ_DIR, "build")
CRAWL_DIR  = os.path.join(BLD_DIR, "mandala", "crawl")

HTML_PATH   = os.path.join(CRAWL_DIR, "fkd", "inf", "mandara.html")
OUTPUT_PATH = os.path.join(BLD_DIR, "mandala", "mandala_taxonomy.json")

# (start_anchor, stop_anchor, dimension_key, neo4j_label, japanese_name)
DIMENSIONS: list[tuple[str, str, str, str, str]] = [
    ("4-a", "4-b", "cause",  "CauseType",  "原因"),
    ("4-b", "4-c", "action", "ActionType", "行動"),
    ("4-c", "5",   "result", "ResultType", "結果"),
]


def extract_items(anchor: Tag, stop_anchor_name: str) -> list[dict]:
    """
    Extract Level-1 and Level-2 items from a Mandala dimension section.

    Iterates over siblings of *anchor* until *stop_anchor_name* is reached.
    Each top-level ``<ul>/<li>`` yields a Level-1 term; nested ``<ul>/<li>``
    items inside it yield Level-2 terms.

    @param anchor: BeautifulSoup tag for the section start anchor.
    @param stop_anchor_name: ``name`` attribute of the anchor that ends this section.
    @return: list of dicts with keys ``name``, ``level``, ``group``, ``children``.
    """
    items: list[dict] = []
    current_group: str = ""

    for tag in anchor.children:
        if not isinstance(tag, Tag):
            continue

        # Stop at the nested child anchor that starts the next section
        if tag.name == "a" and tag.get("name") == stop_anchor_name:
            break

        # Track h4 subgroup (e.g. "個人に起因する原因")
        if tag.name == "h4":
            current_group = tag.get_text(strip=True)
            continue

        if tag.name != "ul":
            continue

        for li in tag.find_all("li", recursive=False):
            strong = li.find("strong")
            if not strong:
                continue

            l1_name = strong.get_text(strip=True)
            children: list[str] = []

            nested_ul = li.find("ul")
            if nested_ul:
                for nested_li in nested_ul.find_all("li", recursive=False):
                    nested_strong = nested_li.find("strong")
                    if nested_strong:
                        children.append(nested_strong.get_text(strip=True))

            items.append({
                "name":     l1_name,
                "level":    1,
                "group":    current_group,
                "children": children,
            })

    return items


def main() -> None:
    """Parse mandara.html and write the Mandala taxonomy to JSON."""
    with open(HTML_PATH, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    taxonomy: dict = {}

    for start_name, stop_name, dimension, label, japanese in DIMENSIONS:
        anchor = soup.find("a", {"name": start_name})
        if not anchor or not isinstance(anchor, Tag):
            LOG.warning("Anchor '%s' not found", start_name)
            continue

        items = extract_items(anchor, stop_name)
        l2_count = sum(len(item["children"]) for item in items)
        LOG.info("%s (%s): %d L1, %d L2", japanese, label, len(items), l2_count)

        taxonomy[dimension] = {
            "label":    label,
            "japanese": japanese,
            "items":    items,
        }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(taxonomy, f, ensure_ascii=False, indent=2)

    LOG.info("Written to %s", OUTPUT_PATH)


if __name__ == "__main__":
    main()
