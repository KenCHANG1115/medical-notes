"""OCR and extract text from First Choice (醫學三) scanned PDFs."""
import pymupdf
import pytesseract
import json
import os
import re
import sys
from PIL import Image
import io
import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "books.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

pytesseract.pytesseract.tesseract_cmd = config["tesseract_cmd"]
os.environ["TESSDATA_PREFIX"] = config["tessdata_dir"]

OUTPUT_BASE = os.path.join(config["output_path"], "first-choice")


def ocr_page(page, lang="chi_tra+eng", dpi=300):
    """Render a PDF page as image and OCR it."""
    mat = pymupdf.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    text = pytesseract.image_to_string(img, lang=lang)
    return text


def process_volume(book_config, volume_label):
    """Process one volume: OCR all pages, save raw text per page."""
    pdf_path = os.path.join(config["library_path"], book_config["filename"])
    lang = book_config["language"]
    vol_dir = os.path.join(OUTPUT_BASE, f"raw-{book_config['id']}")
    os.makedirs(vol_dir, exist_ok=True)

    doc = pymupdf.open(pdf_path)
    total = len(doc)
    print(f"\n{'='*60}")
    print(f"Processing: {volume_label} ({total} pages)")
    print(f"Output: {vol_dir}")
    print(f"{'='*60}")

    progress_file = os.path.join(vol_dir, "_progress.json")
    done_pages = set()
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            done_pages = set(json.load(f).get("done", []))
        print(f"Resuming: {len(done_pages)} pages already done")

    start_time = time.time()
    for i in range(total):
        page_num = i + 1
        if page_num in done_pages:
            continue

        page = doc[i]
        text = ocr_page(page, lang=lang)

        page_file = os.path.join(vol_dir, f"page_{page_num:04d}.txt")
        with open(page_file, "w", encoding="utf-8") as f:
            f.write(text)

        done_pages.add(page_num)

        with open(progress_file, "w") as f:
            json.dump({"done": sorted(done_pages)}, f)

        elapsed = time.time() - start_time
        pages_done = len(done_pages)
        rate = pages_done / elapsed if elapsed > 0 else 0
        remaining = (total - pages_done) / rate if rate > 0 else 0

        if page_num % 10 == 0 or page_num == 1:
            print(f"  [{page_num}/{total}] "
                  f"{pages_done/total*100:.0f}% | "
                  f"{rate:.1f} pages/min | "
                  f"ETA: {remaining/60:.0f} min")

    doc.close()
    return vol_dir


def merge_volume_text(vol_dir, book_config, volume_label):
    """Merge per-page OCR text into a single volume file."""
    pages = sorted(
        f for f in os.listdir(vol_dir)
        if f.startswith("page_") and f.endswith(".txt")
    )

    merged_path = os.path.join(OUTPUT_BASE, f"{book_config['id']}.md")
    with open(merged_path, "w", encoding="utf-8") as out:
        out.write(f"---\n")
        out.write(f'book: "First Choice {volume_label}"\n')
        out.write(f'filename: "{book_config["filename"]}"\n')
        out.write(f"total_pages: {len(pages)}\n")
        out.write(f"---\n\n")

        for page_file in pages:
            page_num = int(page_file.replace("page_", "").replace(".txt", ""))
            page_path = os.path.join(vol_dir, page_file)
            with open(page_path, "r", encoding="utf-8") as f:
                text = f.read().strip()
            if text:
                out.write(f"<!-- page:{page_num} -->\n")
                out.write(text)
                out.write("\n\n")

    print(f"Merged: {merged_path} ({len(pages)} pages)")
    return merged_path


def main():
    fc_books = [b for b in config["books"] if b["id"].startswith("first-choice")]
    os.makedirs(OUTPUT_BASE, exist_ok=True)

    volume_labels = {
        "first-choice-1": "第1冊",
        "first-choice-2": "第2冊",
        "first-choice-3": "第3冊",
        "first-choice-4": "第4冊",
    }

    for book in fc_books:
        label = volume_labels.get(book["id"], book["name"])
        vol_dir = process_volume(book, label)
        merge_volume_text(vol_dir, book, label)

    print(f"\nAll volumes processed. Output: {OUTPUT_BASE}")


if __name__ == "__main__":
    main()
