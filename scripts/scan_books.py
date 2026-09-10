"""Scan PDF books to determine which pages have selectable text vs need OCR."""
import json
import sys
import os
import fitz  # PyMuPDF

def scan_pdf(pdf_path, sample_pages=20):
    """Scan a PDF and classify pages as text-extractable or needing OCR.

    Returns dict with page-level analysis and summary stats.
    """
    doc = fitz.open(pdf_path)
    total = len(doc)

    step = max(1, total // sample_pages)
    sampled_indices = list(range(0, total, step))[:sample_pages]

    text_pages = 0
    ocr_pages = 0
    results = []

    for i in sampled_indices:
        page = doc[i]
        text = page.get_text().strip()
        char_count = len(text)
        has_text = char_count > 50  # threshold: at least 50 chars

        if has_text:
            text_pages += 1
        else:
            ocr_pages += 1

        results.append({
            "page": i + 1,
            "chars": char_count,
            "has_text": has_text,
            "preview": text[:100].replace("\n", " ") if text else "(empty)"
        })

    doc.close()

    text_ratio = text_pages / len(sampled_indices) if sampled_indices else 0

    return {
        "file": os.path.basename(pdf_path),
        "total_pages": total,
        "sampled": len(sampled_indices),
        "text_pages": text_pages,
        "ocr_pages": ocr_pages,
        "text_ratio": round(text_ratio, 2),
        "needs_ocr": text_ratio < 0.8,
        "page_details": results
    }


def main():
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "books.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    library_path = config["library_path"]
    all_results = []

    for book in config["books"]:
        pdf_path = os.path.join(library_path, book["filename"])
        if not os.path.exists(pdf_path):
            print(f"SKIP: {book['filename']} not found")
            continue

        print(f"Scanning: {book['name']}...")
        result = scan_pdf(pdf_path)
        result["book_id"] = book["id"]
        result["book_name"] = book["name"]
        all_results.append(result)

        status = "NEEDS OCR" if result["needs_ocr"] else "TEXT OK"
        print(f"  [{status}] {result['total_pages']} pages, "
              f"{result['text_ratio']*100:.0f}% text-extractable "
              f"(sampled {result['sampled']} pages)")

    output_path = os.path.join(os.path.dirname(__file__), "..", "config", "scan_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\nDetailed results saved to: {output_path}")

    print("\n=== SUMMARY ===")
    for r in all_results:
        status = "NEEDS OCR" if r["needs_ocr"] else "TEXT OK"
        print(f"  {r['book_name']}: [{status}] "
              f"{r['text_ratio']*100:.0f}% text | {r['total_pages']} pages")


if __name__ == "__main__":
    main()
