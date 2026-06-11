"""
FitGirl Repacks Scraper
=======================
Scrapes game repack data from fitgirl-repacks.site and saves to JSON + SQLite.

Usage:
    # First time ever — scrape ALL games from the A-Z page
    python fitgirl_scraper.py --full

    # Daily update — only scrape new games since last run
    python fitgirl_scraper.py --update

    # Scrape latest N listing pages
    python fitgirl_scraper.py --pages 3

    # Scrape a single specific game page
    python fitgirl_scraper.py --url https://fitgirl-repacks.site/outbound/

    # Parse a local HTML file (like your test.html)
    python fitgirl_scraper.py --file test.html

    # Skip SQLite, save JSON only
    python fitgirl_scraper.py --update --no-db

    # Resume a --full run from a specific page (or use saved state automatically)
    python fitgirl_scraper.py --full --resume

Output:
    data/games.json         -> All scraped games as a JSON array
    data/games.db           -> SQLite database for querying/filtering
    data/scrape_state.json  -> Resume pointer for --full runs
"""

import argparse
import json
import re
import sqlite3
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = "https://fitgirl-repacks.site"
AZ_URL   = BASE_URL + "/all-my-repacks-a-z/"
HEADERS  = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}
DELAY_SECONDS  = 2    # polite delay between requests
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES    = 3
RETRY_BACKOFF  = 10   # seconds, multiplied by attempt number


# ── HTML Parsing ──────────────────────────────────────────────────────────────

# def parse_article(article, source_url=""):
#     """Extract all useful fields from a single <article> element."""

#     content = article.select_one(".entry-content")
#     if not content:
#         return None

#     # Title & URL
#     title_el = article.select_one("h1.entry-title, h2.entry-title")
#     title    = title_el.get_text(strip=True) if title_el else None

#     url_el = article.select_one("h1.entry-title a, h2.entry-title a, a[rel='bookmark']")
#     url    = url_el["href"] if url_el else source_url

#     # Date
#     date_el = article.select_one("time.entry-date")
#     date    = date_el.get("datetime", "") if date_el else None

#     # Repack number & version
#     repack_number_el = article.select_one("h3 span[style*='339966']")
#     repack_number    = repack_number_el.get_text(strip=True) if repack_number_el else None

#     version_el = article.select_one("h3 strong span[style*='808080']")
#     version    = version_el.get_text(strip=True) if version_el else None

#     # Cover image
#     cover_el    = content.select_one("img.alignleft")
#     cover_image = cover_el["src"] if cover_el else None

#     # Inline text fields parsed from paragraphs
#     companies     = None
#     languages     = None
#     original_size = None
#     repack_size   = None

#     for p in content.find_all("p"):
#         p_text = p.get_text(" ")
#         if "Companies:" in p_text and not companies:
#             m = re.search(r"Companies:\s*(.+?)(?:\n|Languages:|$)", p_text)
#             if m: companies = m.group(1).strip()
#         if "Languages:" in p_text and not languages:
#             m = re.search(r"Languages:\s*(.+?)(?:\n|Original|$)", p_text)
#             if m: languages = m.group(1).strip()
#         if "Original Size:" in p_text and not original_size:
#             m = re.search(r"Original Size:\s*(.+?)(?:\n|Repack|$)", p_text)
#             if m: original_size = m.group(1).strip()
#         if "Repack Size:" in p_text and not repack_size:
#             m = re.search(r"Repack Size:\s*(.+?)(?:\n|$)", p_text)
#             if m: repack_size = m.group(1).strip()

#     # Genres/Tags
#     genres = list(dict.fromkeys(
#         a.get_text(strip=True)
#         for a in content.select("a[href*='/tag/']")
#     ))

#     # Screenshots
#     screenshots = []
#     for h3 in content.find_all("h3"):
#         if "screenshot" in h3.get_text().lower():
#             section = h3.find_next_sibling("p")
#             if section:
#                 screenshots = [
#                     img["src"] for img in section.find_all("img") if img.get("src")
#                 ]
#             break

#     # Trailer
#     video_src = content.select_one("video source")
#     trailer   = video_src.get("src") if video_src else None

#     # Download mirrors
#     def get_mirrors(heading_keyword):
#         mirrors = []
#         for h3 in content.find_all("h3"):
#             if heading_keyword.lower() in h3.get_text().lower():
#                 ul = h3.find_next_sibling("ul")
#                 if ul:
#                     for li in ul.find_all("li", recursive=False):
#                         top_link     = li.find("a")
#                         hoster       = top_link.get_text(strip=True) if top_link else "Unknown"
#                         hoster_url   = top_link["href"] if top_link else None
#                         direct_files = []
#                         spoiler = li.select_one(".su-spoiler-content")
#                         if spoiler:
#                             direct_files = [
#                                 {"name": a.get_text(strip=True), "url": a["href"]}
#                                 for a in spoiler.find_all("a", href=True)
#                             ]
#                         mirrors.append({
#                             "hoster": hoster,
#                             "url": hoster_url,
#                             "direct_files": direct_files,
#                         })
#         return mirrors

#     direct_mirrors  = get_mirrors("Direct Links")
#     torrent_mirrors = get_mirrors("Torrent")

#     # Repack features
#     repack_features = []
#     for h3 in content.find_all("h3"):
#         if "repack features" in h3.get_text().lower():
#             ul = h3.find_next_sibling("ul")
#             if ul:
#                 repack_features = [li.get_text(strip=True) for li in ul.find_all("li")]
#             break

#     # Game description
#     description = None
#     for spoiler in content.select(".su-spoiler"):
#         spoiler_title = spoiler.select_one(".su-spoiler-title")
#         if spoiler_title and "game description" in spoiler_title.get_text().lower():
#             body = spoiler.select_one(".su-spoiler-content")
#             if body:
#                 description = body.get_text(" ", strip=True)
#             break

#     return {
#         "title":           title,
#         "url":             url,
#         "date":            date,
#         "repack_number":   repack_number,
#         "version":         version,
#         "cover_image":     cover_image,
#         "genres":          genres,
#         "companies":       companies,
#         "languages":       languages,
#         "original_size":   original_size,
#         "repack_size":     repack_size,
#         "screenshots":     screenshots,
#         "trailer":         trailer,
#         "direct_mirrors":  direct_mirrors,
#         "torrent_mirrors": torrent_mirrors,
#         "repack_features": repack_features,
#         "description":     description,
#     }

def parse_article(article, source_url=""):
    """Extract all useful fields from a single <article> element."""
 
    content = article.select_one(".entry-content")
    if not content:
        return None
 
    # Title & URL
    title_el = article.select_one("h1.entry-title, h2.entry-title")
    title    = title_el.get_text(strip=True) if title_el else None
 
    url_el = article.select_one("h1.entry-title a, h2.entry-title a, a[rel='bookmark']")
    url    = url_el["href"] if url_el else source_url
 
    # Date
    date_el = article.select_one("time.entry-date")
    date    = date_el.get("datetime", "") if date_el else None
 
    # Repack number & version
    repack_number_el = article.select_one("h3 span[style*='339966']")
    repack_number    = repack_number_el.get_text(strip=True) if repack_number_el else None
 
    version_el = article.select_one("h3 strong span[style*='808080']")
    version    = version_el.get_text(strip=True) if version_el else None
 
    # Cover image
    cover_el    = content.select_one("img.alignleft")
    cover_image = cover_el["src"] if cover_el else None
 
    # Inline text fields parsed from paragraphs
    companies     = None
    languages     = None
    original_size = None
    repack_size   = None
 
    for p in content.find_all("p"):
        p_text = p.get_text(" ")
        if "Companies:" in p_text and not companies:
            m = re.search(r"Companies:\s*(.+?)(?:\n|Languages:|$)", p_text)
            if m: companies = m.group(1).strip()
        if "Languages:" in p_text and not languages:
            m = re.search(r"Languages:\s*(.+?)(?:\n|Original|$)", p_text)
            if m: languages = m.group(1).strip()
        if "Original Size:" in p_text and not original_size:
            m = re.search(r"Original Size:\s*(.+?)(?:\n|Repack|$)", p_text)
            if m: original_size = m.group(1).strip()
        if "Repack Size:" in p_text and not repack_size:
            m = re.search(r"Repack Size:\s*(.+?)(?:\n|$)", p_text)
            if m: repack_size = m.group(1).strip()
 
    # Genres/Tags
    genres = list(dict.fromkeys(
        a.get_text(strip=True)
        for a in content.select("a[href*='/tag/']")
    ))
 
    # Screenshots
    screenshots = []
    for h3 in content.find_all("h3"):
        if "screenshot" in h3.get_text().lower():
            section = h3.find_next_sibling("p")
            if section:
                screenshots = [
                    img["src"] for img in section.find_all("img") if img.get("src")
                ]
            break
 
    # Trailer
    video_src = content.select_one("video source")
    trailer   = video_src.get("src") if video_src else None
 
    # Download mirrors
    TORRENT_HOSTER_HINTS = (
        "1337x", "rutor", "rutracker", "tapochek", "torrent", "nyaa",
        "kickass", "magnet",
    )
 
    def parse_mirror_li(li):
        top_link     = li.find("a")
        hoster       = top_link.get_text(strip=True) if top_link else "Unknown"
        hoster_url   = top_link["href"] if top_link else None
        direct_files = []
        spoiler = li.select_one(".su-spoiler-content")
        if spoiler:
            direct_files = [
                {"name": a.get_text(strip=True), "url": a["href"]}
                for a in spoiler.find_all("a", href=True)
            ]
        return {
            "hoster": hoster,
            "url": hoster_url,
            "direct_files": direct_files,
        }
 
    def is_torrent_mirror(li, mirror):
        text = li.get_text(" ").lower()
        hoster = (mirror.get("hoster") or "").lower()
        if any(hint in hoster for hint in TORRENT_HOSTER_HINTS):
            return True
        if any(hint in text for hint in TORRENT_HOSTER_HINTS):
            return True
        return False
 
    def get_mirrors(heading_keyword):
        mirrors = []
        for h3 in content.find_all("h3"):
            if heading_keyword.lower() in h3.get_text().lower():
                ul = h3.find_next_sibling("ul")
                if ul:
                    for li in ul.find_all("li", recursive=False):
                        mirrors.append(parse_mirror_li(li))
        return mirrors
 
    direct_mirrors  = get_mirrors("Direct Links")
    torrent_mirrors = get_mirrors("Torrent")
 
    # Older posts use a single "Download Mirrors" heading containing both
    # direct-link and torrent entries in one <ul>. Fall back to that and
    # split entries by hoster/content heuristics.
    if not direct_mirrors and not torrent_mirrors:
        for h3 in content.find_all("h3"):
            h3_text = h3.get_text().lower()
            if "download mirror" in h3_text:
                ul = h3.find_next_sibling("ul")
                if ul:
                    for li in ul.find_all("li", recursive=False):
                        mirror = parse_mirror_li(li)
                        if is_torrent_mirror(li, mirror):
                            torrent_mirrors.append(mirror)
                        else:
                            direct_mirrors.append(mirror)
                break
 
    # Repack features
    repack_features = []
    for h3 in content.find_all("h3"):
        if "repack features" in h3.get_text().lower():
            ul = h3.find_next_sibling("ul")
            if ul:
                repack_features = [li.get_text(strip=True) for li in ul.find_all("li")]
            break
 
    # Game description
    description = None
    for spoiler in content.select(".su-spoiler"):
        spoiler_title = spoiler.select_one(".su-spoiler-title")
        if spoiler_title and "game description" in spoiler_title.get_text().lower():
            body = spoiler.select_one(".su-spoiler-content")
            if body:
                description = body.get_text(" ", strip=True)
            break
 
    return {
        "title":           title,
        "url":             url,
        "date":            date,
        "repack_number":   repack_number,
        "version":         version,
        "cover_image":     cover_image,
        "genres":          genres,
        "companies":       companies,
        "languages":       languages,
        "original_size":   original_size,
        "repack_size":     repack_size,
        "screenshots":     screenshots,
        "trailer":         trailer,
        "direct_mirrors":  direct_mirrors,
        "torrent_mirrors": torrent_mirrors,
        "repack_features": repack_features,
        "description":     description,
    }
 


# ── Fetching ──────────────────────────────────────────────────────────────────

def fetch_html(url, retries=MAX_RETRIES, backoff=RETRY_BACKOFF):
    """Fetch a URL with retries and exponential-ish backoff on failure."""
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as e:
            last_exc = e
            print(f"    [!] Attempt {attempt}/{retries} failed for {url}: {e}")
            if attempt < retries:
                wait = backoff * attempt
                print(f"    ... retrying in {wait}s")
                time.sleep(wait)
    raise last_exc


def get_game_urls_from_page(url):
    """Return (list of game URLs, next page URL or None) from a listing page."""
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    ul_list = soup.select_one("ul#lcp_instance_0")
    links = []
    if ul_list:
        for game in ul_list.find_all("li"):
            # print(game)
            a = game.select_one("a")
            if a and a.get("href"):
                links.append(a["href"])
    else:
        # Fallback: regular blog listing layout (articles directly on the page)
        for article in soup.select("article"):
            a = article.select_one("h1.entry-title a, h2.entry-title a, a[rel='bookmark']")
            if a and a.get("href"):
                links.append(a["href"])

    next_el  = soup.select_one("a.lcp_nextlink") or soup.select_one("a.next.page-numbers")
    next_url = next_el["href"] if next_el else None

    return links, next_url


def scrape_game_page(url):
    html    = fetch_html(url)
    soup    = BeautifulSoup(html, "html.parser")
    article = soup.select_one("article")
    if not article:
        print(f"  [!] No article found at {url}")
        return None
    return parse_article(article, source_url=url)


def scrape_local_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()
    soup    = BeautifulSoup(html, "html.parser")
    article = soup.select_one("article") or soup
    return parse_article(article, source_url=filepath)


# ── SQLite ────────────────────────────────────────────────────────────────────

def init_db(db_path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT,
            url             TEXT UNIQUE,
            date            TEXT,
            repack_number   TEXT,
            version         TEXT,
            cover_image     TEXT,
            genres          TEXT,
            companies       TEXT,
            languages       TEXT,
            original_size   TEXT,
            repack_size     TEXT,
            screenshots     TEXT,
            trailer         TEXT,
            direct_mirrors  TEXT,
            torrent_mirrors TEXT,
            repack_features TEXT,
            description     TEXT,
            scraped_at      TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def url_exists(conn, url):
    """Return True if this game URL is already in the DB."""
    row = conn.execute("SELECT 1 FROM games WHERE url=?", (url,)).fetchone()
    return row is not None


def upsert_game(conn, game):
    conn.execute("""
        INSERT INTO games (
            title, url, date, repack_number, version, cover_image,
            genres, companies, languages, original_size, repack_size,
            screenshots, trailer, direct_mirrors, torrent_mirrors,
            repack_features, description
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(url) DO UPDATE SET
            title=excluded.title, date=excluded.date,
            repack_number=excluded.repack_number, version=excluded.version,
            cover_image=excluded.cover_image, genres=excluded.genres,
            companies=excluded.companies, languages=excluded.languages,
            original_size=excluded.original_size, repack_size=excluded.repack_size,
            screenshots=excluded.screenshots, trailer=excluded.trailer,
            direct_mirrors=excluded.direct_mirrors,
            torrent_mirrors=excluded.torrent_mirrors,
            repack_features=excluded.repack_features,
            description=excluded.description,
            scraped_at=datetime('now')
    """, (
        game.get("title"),         game.get("url"),
        game.get("date"),          game.get("repack_number"),
        game.get("version"),       game.get("cover_image"),
        json.dumps(game.get("genres",          []), ensure_ascii=False),
        game.get("companies"),     game.get("languages"),
        game.get("original_size"), game.get("repack_size"),
        json.dumps(game.get("screenshots",     []), ensure_ascii=False),
        game.get("trailer"),
        json.dumps(game.get("direct_mirrors",  []), ensure_ascii=False),
        json.dumps(game.get("torrent_mirrors", []), ensure_ascii=False),
        json.dumps(game.get("repack_features", []), ensure_ascii=False),
        game.get("description"),
    ))
    conn.commit()


# ── Save helpers ──────────────────────────────────────────────────────────────

def save_json(games, path):
    """Merge new games with existing JSON file."""
    existing = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        existing_urls = {g["url"] for g in existing}
        games = [g for g in games if g["url"] not in existing_urls] + existing

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)
    print(f"  JSON -> {path}  ({len(games)} total games)")


# ── Resume state helpers ──────────────────────────────────────────────────────

def state_path(out_dir):
    return Path(out_dir) / "scrape_state.json"


def save_state(out_dir, current_url, page_num):
    p = state_path(out_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"current_url": current_url, "page_num": page_num}), encoding="utf-8")


def load_state(out_dir):
    p = state_path(out_dir)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def clear_state(out_dir):
    p = state_path(out_dir)
    if p.exists():
        p.unlink()


# ── Scraping modes ────────────────────────────────────────────────────────────

def run_full(conn, out_dir, resume=False, start_url=None):
    """
    --full
    Paginates through the entire A-Z listing and scrapes every game.
    Skips URLs already in the DB so it is safe to re-run if interrupted.
    Use this once on first run.

    If resume=True, picks up from data/scrape_state.json (if present).
    If start_url is given, starts from that listing page instead.
    """
    print("\n📚 FULL SCRAPE — A-Z listing")
    print("   This will take a long time. Ctrl+C to stop; re-run with --resume to continue.\n")

    games    = []
    page_num = 1
    current_url = AZ_URL

    if start_url:
        current_url = start_url
        print(f"   Starting from explicit URL: {current_url}\n")
    elif resume:
        state = load_state(out_dir)
        if state:
            current_url = state["current_url"]
            page_num    = state["page_num"]
            print(f"   Resuming from page {page_num}: {current_url}\n")
        else:
            print("   No saved state found, starting from the beginning.\n")

    while current_url:
        print(f"📃 Listing page {page_num}: {current_url}")
        save_state(out_dir, current_url, page_num)

        try:
            game_urls, next_url = get_game_urls_from_page(current_url)
        except Exception as e:
            print(f"  [!] Failed to fetch listing after retries: {e}")
            print(f"  [!] Stopping. Re-run with --full --resume to continue from this page.")
            break

        print(f"  Found {len(game_urls)} links on this page")

        for game_url in game_urls:
            if conn and url_exists(conn, game_url):
                print(f"  ⏭  Already in DB, skipping")
                continue
            try:
                print(f"  Fetching: {game_url}")
                game = scrape_game_page(game_url)
                if game:
                    games.append(game)
                    if conn:
                        upsert_game(conn, game)
                    print(f"  ✓ {game.get('repack_number', '')} {game.get('title')}")
                time.sleep(DELAY_SECONDS)
            except Exception as e:
                print(f"  [!] Failed: {game_url} -> {e}")

        current_url = next_url
        page_num   += 1
        if current_url:
            time.sleep(DELAY_SECONDS)

    if not current_url:
        # Reached the end successfully — clear resume state
        clear_state(out_dir)
        print("\n  ✅ Reached the end of the A-Z listing.")

    return games


def run_update(conn):
    """
    --update
    Scrapes the homepage (newest posts first).
    Stops automatically the moment it hits a URL already in the DB.
    Run this daily or weekly.
    """
    print("\n🔄 UPDATE — checking for new games\n")

    games       = []
    current_url = BASE_URL
    page_num    = 1
    done        = False

    while current_url and not done:
        print(f"📃 Page {page_num}: {current_url}")
        try:
            game_urls, next_url = get_game_urls_from_page(current_url)
        except Exception as e:
            print(f"  [!] Failed to fetch listing after retries: {e}")
            break

        for game_url in game_urls:
            if conn and url_exists(conn, game_url):
                # Everything from here onward is already saved — stop
                print(f"  ⏹  Already in DB — all caught up!")
                done = True
                break
            try:
                print(f"  Fetching: {game_url}")
                game = scrape_game_page(game_url)
                if game:
                    games.append(game)
                    if conn:
                        upsert_game(conn, game)
                    print(f"  ✓ {game.get('repack_number', '')} {game.get('title')}")
                time.sleep(DELAY_SECONDS)
            except Exception as e:
                print(f"  [!] Failed: {game_url} -> {e}")

        if not done:
            current_url = next_url
            page_num   += 1
            if current_url:
                time.sleep(DELAY_SECONDS)

    if not games:
        print("  ✓ Already up to date — no new games found")

    return games


def run_pages(n_pages, conn):
    """--pages N: Scrape the newest N listing pages from the homepage."""
    print(f"\n🔍 Scraping {n_pages} listing page(s)\n")

    games       = []
    current_url = BASE_URL
    pages_done  = 0

    while current_url and pages_done < n_pages:
        print(f"📃 Page {pages_done + 1}: {current_url}")
        try:
            game_urls, next_url = get_game_urls_from_page(current_url)
        except Exception as e:
            print(f"  [!] Failed after retries: {e}")
            break

        for game_url in game_urls:
            if conn and url_exists(conn, game_url):
                print(f"  ⏭  Already in DB, skipping")
                continue
            try:
                print(f"  Fetching: {game_url}")
                game = scrape_game_page(game_url)
                if game:
                    games.append(game)
                    if conn:
                        upsert_game(conn, game)
                    print(f"  ✓ {game.get('repack_number', '')} {game.get('title')}")
                time.sleep(DELAY_SECONDS)
            except Exception as e:
                print(f"  [!] Failed: {game_url} -> {e}")

        current_url = next_url
        pages_done += 1
        if current_url:
            time.sleep(DELAY_SECONDS)

    return games


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape FitGirl Repacks into JSON + SQLite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fitgirl_scraper.py --full
  python fitgirl_scraper.py --full --resume
  python fitgirl_scraper.py --full --start-url https://fitgirl-repacks.site/page/164/
  python fitgirl_scraper.py --update
  python fitgirl_scraper.py --pages 3
  python fitgirl_scraper.py --url https://fitgirl-repacks.site/outbound/
  python fitgirl_scraper.py --file test.html
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--full",   action="store_true", help="Full scrape from A-Z (first run only)")
    group.add_argument("--update", action="store_true", help="Only scrape new games since last run")
    group.add_argument("--pages",  type=int,            help="Scrape newest N listing pages")
    group.add_argument("--url",    type=str,            help="Scrape a single game URL")
    group.add_argument("--file",   type=str,            help="Parse a local HTML file")

    parser.add_argument("--no-db",     action="store_true", help="Skip SQLite, save JSON only")
    parser.add_argument("--out",       type=str, default="data", help="Output directory (default: data/)")
    parser.add_argument("--resume",    action="store_true", help="With --full, resume from saved state")
    parser.add_argument("--start-url", type=str, default=None,
                         help="With --full, start from this listing page URL instead of the beginning")

    args      = parser.parse_args()
    out_dir   = Path(args.out)
    json_path = out_dir / "games.json"
    db_path   = out_dir / "games.db"

    # Open DB early so we can check existing URLs while scraping
    conn = None
    if not args.no_db:
        conn = init_db(db_path)

    # ── Run chosen mode ───────────────────────────────────────────────────────
    games = []

    if args.file:
        print(f"\n📄 Parsing local file: {args.file}")
        game = scrape_local_file(args.file)
        if game:
            games.append(game)
            if conn:
                upsert_game(conn, game)
            print(f"  ✓ {game.get('title')}")

    elif args.url:
        print(f"\n🌐 Scraping: {args.url}")
        game = scrape_game_page(args.url)
        if game:
            games.append(game)
            if conn:
                upsert_game(conn, game)
            print(f"  ✓ {game.get('title')}")

    elif args.full:
        games = run_full(conn, out_dir, resume=args.resume, start_url=args.start_url)

    elif args.update:
        games = run_update(conn)

    elif args.pages:
        games = run_pages(args.pages, conn)

    # ── Save JSON ─────────────────────────────────────────────────────────────
    if games:
        print(f"\n💾 Saving...")
        save_json(games, json_path)

    # ── Final DB count ────────────────────────────────────────────────────────
    if conn:
        total = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        print(f"  DB  -> {db_path}  ({total} total games)")
        conn.close()

    if not games:
        print("\n✓ Nothing new to save.")
        return

    # ── Sample output ─────────────────────────────────────────────────────────
    s = games[0]
    print("\n── Sample (first new game) ──────────────────────────────")
    print(f"  Title:         {s.get('title')}")
    print(f"  Date:          {s.get('date')}")
    print(f"  Languages:     {s.get('languages')}")
    print(f"  Original Size: {s.get('original_size')}")
    print(f"  Repack Size:   {s.get('repack_size')}")
    print(f"  Genres:        {', '.join(s.get('genres', []))}")
    print(f"  Screenshots:   {len(s.get('screenshots', []))} images")
    print("─────────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
