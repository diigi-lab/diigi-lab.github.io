import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random
import os

SCHOLAR_ID = "jR3NLMsAAAAJ"
MAX_PUBS = 10  # number of recent publications to display
OUTPUT_HTML = "index.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_publications(scholar_id, max_results=10):
    """Fetch publications from Google Scholar sorted by date."""
    url = (
        f"https://scholar.google.com/citations"
        f"?hl=en&user={scholar_id}&view_op=list_works&sortby=pubdate"
        f"&cstart=0&pagesize={max_results}"
    )

    time.sleep(random.uniform(2, 5))

    response = requests.get(url, headers=HEADERS, timeout=30)

    if response.status_code != 200:
        print(f"Error: Status code {response.status_code}")
        print("Trying fallback with scholarly library...")
        return fetch_with_scholarly(scholar_id, max_results)

    soup = BeautifulSoup(response.text, "html.parser")
    publications = []

    rows = soup.select("tr.gsc_a_tr")

    if not rows:
        print("No publications found via scraping. Trying scholarly...")
        return fetch_with_scholarly(scholar_id, max_results)

    for row in rows[:max_results]:
        title_tag = row.select_one("a.gsc_a_at")
        authors_tag = row.select_one("div.gs_gray")
        venue_tag = row.select_one("div.gs_gray + div.gs_gray")
        year_tag = row.select_one("span.gsc_a_h.gsc_a_hc.gs_ibl")

        title = title_tag.text.strip() if title_tag else ""
        link = (
            "https://scholar.google.com" + title_tag["href"]
            if title_tag and title_tag.get("href")
            else ""
        )
        authors = authors_tag.text.strip() if authors_tag else ""
        venue = venue_tag.text.strip() if venue_tag else ""
        year = year_tag.text.strip() if year_tag else ""

        if title:
            publications.append({
                "title": title,
                "authors": authors,
                "venue": venue,
                "year": year,
                "link": link,
            })

    return publications


def fetch_with_scholarly(scholar_id, max_results=10):
    """Fallback: Use scholarly library."""
    try:
        from scholarly import scholarly

        author = scholarly.search_author_id(scholar_id)
        author = scholarly.fill(author, sections=["publications"])

        publications = []
        pubs = sorted(
            author["publications"],
            key=lambda x: x.get("bib", {}).get("pub_year", "0"),
            reverse=True,
        )

        for pub in pubs[:max_results]:
            bib = pub.get("bib", {})
            publications.append({
                "title": bib.get("title", ""),
                "authors": bib.get("author", ""),
                "venue": bib.get("journal", bib.get("booktitle", "")),
                "year": bib.get("pub_year", ""),
                "link": pub.get("pub_url", ""),
            })

        return publications

    except ImportError:
        print("scholarly not installed. Install with: pip install scholarly")
        return []
    except Exception as e:
        print(f"scholarly error: {e}")
        return []


def generate_pub_html(publications):
    """Generate HTML list items for publications."""
    items = []
    for pub in publications:
        authors = pub["authors"]
        title = pub["title"]
        venue = pub["venue"]
        year = pub["year"]
        link = pub["link"]

        # Build citation string
        citation = f'{authors}, "{title}"'
        if venue:
            citation += f", <em>{venue}</em>"
        if year:
            citation += f" ({year})"
        citation += "."

        if link:
            citation += f' <a href="{link}" target="_blank">[Link]</a>'

        items.append(f"            <li>{citation}</li>")

    return "\n".join(items)


def update_html(pub_html):
    """Replace the publications list in index.html."""
    if not os.path.exists(OUTPUT_HTML):
        print(f"Error: {OUTPUT_HTML} not found")
        return False

    with open(OUTPUT_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    # Pattern to match content between <ol class="pub-list"> and </ol>
    pattern = r'(<ol class="pub-list">)(.*?)(</ol>)'
    replacement = rf'\1\n{pub_html}\n        \3'

    new_html, count = re.subn(pattern, replacement, html, flags=re.DOTALL)

    if count == 0:
        print("Error: Could not find pub-list in HTML")
        return False

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"Updated {count} publication section(s)")
    return True


def save_json_backup(publications):
    """Save publications as JSON for reference."""
    os.makedirs("data", exist_ok=True)
    with open("data/publications.json", "w", encoding="utf-8") as f:
        json.dump(publications, f, indent=2, ensure_ascii=False)
    print("Saved data/publications.json")


def main():
    print(f"Fetching publications for scholar ID: {SCHOLAR_ID}")
    print(f"Max publications: {MAX_PUBS}")

    publications = fetch_publications(SCHOLAR_ID, MAX_PUBS)

    if not publications:
        print("No publications fetched. Exiting without changes.")
        return

    print(f"Fetched {len(publications)} publications:")
    for i, pub in enumerate(publications, 1):
        print(f"  {i}. {pub['title']} ({pub['year']})")

    # Save JSON backup
    save_json_backup(publications)

    # Generate and inject HTML
    pub_html = generate_pub_html(publications)
    success = update_html(pub_html)

    if success:
        print("HTML updated successfully!")
    else:
        print("Failed to update HTML.")


if __name__ == "__main__":
    main()
