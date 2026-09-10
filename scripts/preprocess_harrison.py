"""Extract and split Harrison's by chapters using PDF bookmarks."""
import pymupdf
import json
import os
import re

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "books.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

PDF_PATH = os.path.join(config["library_path"], config["books"][0]["filename"])
OUTPUT_BASE = os.path.join(config["output_path"], "harrison")


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:80].strip('-')


def extract_chapters(doc, toc):
    """Parse TOC into chapter entries with page ranges."""
    chapters = []
    current_part = ""
    current_section = ""

    for i, entry in enumerate(toc):
        level, title, start_page = entry

        if level == 1:
            if title.startswith("PART"):
                current_part = title
                current_section = ""
            continue

        if level == 2:
            if title.startswith("SECTION"):
                current_section = title
                continue

            # L2 chapter (in Part 1 which has no sections)
            end_page = toc[i + 1][2] if i + 1 < len(toc) else len(doc)
            chapters.append({
                "part": current_part,
                "section": current_section,
                "title": title,
                "start_page": start_page,
                "end_page": end_page,
            })
            continue

        if level == 3:
            end_page = toc[i + 1][2] if i + 1 < len(toc) else len(doc)
            chapters.append({
                "part": current_part,
                "section": current_section,
                "title": title,
                "start_page": start_page,
                "end_page": end_page,
            })

    return chapters


def extract_text_range(doc, start, end):
    """Extract text from page range [start, end) (1-indexed)."""
    texts = []
    for p in range(start - 1, min(end - 1, len(doc))):
        page = doc[p]
        text = page.get_text()
        if text.strip():
            texts.append(text)
    return "\n\n".join(texts)


def save_chapter(chapter, text, index):
    """Save chapter as Markdown with metadata frontmatter."""
    part_slug = slugify(chapter["part"]) if chapter["part"] else "front-matter"
    chapter_slug = slugify(chapter["title"])

    out_dir = os.path.join(OUTPUT_BASE, part_slug)
    os.makedirs(out_dir, exist_ok=True)

    filename = f"{index:03d}-{chapter_slug}.md"
    filepath = os.path.join(out_dir, filename)

    frontmatter = f"""---
book: "Harrison's Principles of Internal Medicine, 22nd Edition"
part: "{chapter['part']}"
section: "{chapter['section']}"
chapter: "{chapter['title']}"
pages: "{chapter['start_page']}-{chapter['end_page'] - 1}"
---

# {chapter['title']}

"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter + text)

    return filepath


def main():
    print(f"Opening: {PDF_PATH}")
    doc = pymupdf.open(PDF_PATH)
    toc = doc.get_toc()

    print(f"Pages: {len(doc)}, TOC entries: {len(toc)}")

    chapters = extract_chapters(doc, toc)
    print(f"Chapters identified: {len(chapters)}")

    os.makedirs(OUTPUT_BASE, exist_ok=True)

    manifest = []
    for i, ch in enumerate(chapters):
        text = extract_text_range(doc, ch["start_page"], ch["end_page"])
        filepath = save_chapter(ch, text, i + 1)
        rel_path = os.path.relpath(filepath, OUTPUT_BASE)

        manifest.append({
            "index": i + 1,
            "title": ch["title"],
            "part": ch["part"],
            "section": ch["section"],
            "pages": f"{ch['start_page']}-{ch['end_page'] - 1}",
            "file": rel_path,
            "char_count": len(text),
        })

        if (i + 1) % 50 == 0 or i == 0:
            print(f"  [{i+1}/{len(chapters)}] {ch['title'][:60]}...")

    manifest_path = os.path.join(OUTPUT_BASE, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    doc.close()

    total_chars = sum(m["char_count"] for m in manifest)
    print(f"\nDone! {len(chapters)} chapters extracted")
    print(f"Total characters: {total_chars:,}")
    print(f"Output: {OUTPUT_BASE}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
