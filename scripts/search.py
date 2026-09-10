"""Search the book library for content related to a disease/topic."""
import json
import os
import re
import sys
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "..", "config", "books.json")
HARRISON_MANIFEST = os.path.join(SCRIPT_DIR, "..", "book-library", "harrison", "manifest.json")
FC_MANIFEST = os.path.join(SCRIPT_DIR, "..", "book-library", "first-choice", "manifest.json")
BOOK_LIBRARY = os.path.join(SCRIPT_DIR, "..", "book-library")


def load_manifests():
    manifests = {}
    if os.path.exists(HARRISON_MANIFEST):
        with open(HARRISON_MANIFEST, "r", encoding="utf-8") as f:
            manifests["harrison"] = json.load(f)
    if os.path.exists(FC_MANIFEST):
        with open(FC_MANIFEST, "r", encoding="utf-8") as f:
            manifests["first-choice"] = json.load(f)
    return manifests


def search_chapters(query, manifests, max_results=10):
    """Search chapter titles and content for the query terms.

    Returns list of {book, title, file, relevance, snippet}.
    """
    query_lower = query.lower().strip()
    terms = re.split(r'[\s/,、]+', query_lower)
    terms = [t for t in terms if len(t) >= 2]

    results = []

    for book_id, entries in manifests.items():
        base_dir = os.path.join(BOOK_LIBRARY, book_id)

        for entry in entries:
            title = entry.get("title", entry.get("topic", ""))
            title_lower = title.lower()
            score = 0

            # Full phrase match in title (highest priority)
            if query_lower in title_lower:
                score += 20

            # Individual term match in title (weight by term length)
            for t in terms:
                if t in title_lower:
                    score += 3 + len(t)

            # Section/part match
            section = entry.get("section", entry.get("specialty", "")).lower()
            for t in terms:
                if t in section:
                    score += 1

            if score == 0:
                filepath = os.path.join(base_dir, entry["file"])
                if not os.path.exists(filepath):
                    continue
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read(50000).lower()
                # Full phrase in content
                phrase_count = content.count(query_lower)
                if phrase_count > 0:
                    score += 5 + phrase_count
                else:
                    term_hits = sum(1 for t in terms if t in content)
                    if term_hits == len(terms):
                        score += 3
                    elif term_hits > 0:
                        score += term_hits * 0.3
                if score == 0:
                    continue

            results.append({
                "book": book_id,
                "title": title,
                "file": entry["file"],
                "filepath": os.path.join(base_dir, entry["file"]),
                "pages": entry.get("pages", ""),
                "section": entry.get("part", entry.get("specialty", "")),
                "relevance": score,
                "char_count": entry.get("char_count", 0),
            })

    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:max_results]


def get_chapter_content(filepath, max_chars=None):
    """Read a chapter file, stripping frontmatter."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # Strip YAML frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:].strip()
    if max_chars:
        content = content[:max_chars]
    return content


def search_and_retrieve(query, books=None, max_results=8, max_chars_per_chapter=30000):
    """Search and retrieve content for note generation.

    Args:
        query: disease/topic name
        books: list of book IDs to search (None = all)
        max_results: max chapters to return
        max_chars_per_chapter: max chars per chapter content

    Returns:
        list of {book, title, section, pages, content}
    """
    manifests = load_manifests()
    if books:
        manifests = {k: v for k, v in manifests.items() if k in books}

    results = search_chapters(query, manifests, max_results)

    retrieved = []
    for r in results:
        content = get_chapter_content(r["filepath"], max_chars_per_chapter)
        retrieved.append({
            "book": "Harrison's 22e" if r["book"] == "harrison" else "First Choice 醫學(三)",
            "title": r["title"],
            "section": r["section"],
            "pages": r["pages"],
            "content": content,
            "relevance": r["relevance"],
        })

    return retrieved


def main():
    if len(sys.argv) < 2:
        print("Usage: python search.py <disease name>")
        print("Example: python search.py 'Nephrotic Syndrome'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"Searching for: {query}\n")

    results = search_and_retrieve(query)

    if not results:
        print("No results found.")
        return

    print(f"Found {len(results)} relevant chapters:\n")
    for i, r in enumerate(results, 1):
        print(f"  {i}. [{r['book']}] {r['title']}")
        print(f"     Section: {r['section']} | Pages: {r['pages']}")
        print(f"     Content: {len(r['content']):,} chars | Relevance: {r['relevance']}")
        print()


if __name__ == "__main__":
    main()
