import hashlib
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
import logging 

import click
import requests
from bs4 import BeautifulSoup

LOG = logging.getLogger(__name__)


def url_to_path(output_dir: Path, url: str) -> Path:
    """Map a URL to a local file path under output_dir, mirroring the URL structure.

    @param output_dir: Root directory where files are saved.
    @param url: Absolute URL to map.
    @return: Local file path corresponding to the URL.
    """
    parsed = urlparse(url)
    # Use URL path as file path; fall back to index.html for bare directories
    url_path = parsed.path.strip("/") or "index"
    if not Path(url_path).suffix:
        url_path += ".html"
    # Sanitise segments that are too long for the filesystem
    parts = Path(url_path).parts
    safe_parts = [p[:200] for p in parts]
    return output_dir / Path(*safe_parts)


def crawl(start_url: str, output_dir: Path, delay: float = 0.5) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    base = urlparse(start_url)
    allowed_netloc = base.netloc

    visited: set[str] = set()
    queue: list[str] = [start_url]

    session = requests.Session()
    session.headers["User-Agent"] = "site-crawler/1.0"

    n = 0

    while queue:
        url = queue.pop(0)
        # Normalise: strip fragment
        url = url.split("#")[0].rstrip("/") or url

        n += 1

        if url in visited:
            continue
        visited.add(url)

        dest = url_to_path(output_dir, url)
        if dest.exists():
            LOG.info("[%d] Already downloaded: %s", n, dest)
            raw = dest.read_text(encoding="utf-8", errors="replace")
        else:
            LOG.info("[%d] Fetching %s", n, url)
            try:
                resp = session.get(url, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as exc:
                LOG.warning("Failed: SKIP %s: %s", url, exc)
                continue

            content_type = resp.headers.get("Content-Type", "")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
            LOG.info("  -> %s", dest)

            if "text/html" not in content_type:
                LOG.debug("Saved non-HTML (%s), skipping link extraction", content_type)
                continue

            raw = resp.text

        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            absolute = urljoin(url, href).split("#")[0].rstrip("/")
            parsed = urlparse(absolute)
            if parsed.netloc == allowed_netloc and absolute not in visited:
                queue.append(absolute)

        time.sleep(delay)

    LOG.info("Done. %d URLs visited, output in %s", len(visited), output_dir)


@click.command(no_args_is_help=True)
@click.argument("url")
@click.option("--output", "-o", default="crawled", show_default=True, help="Output directory.")
@click.option("--delay", "-d", default=0.5, show_default=True, help="Seconds between requests.")
def main(url: str, output: str, delay: float) -> None:
    """Crawl a site and save HTML pages."""
    crawl(url, Path(output), delay=delay)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    main()
