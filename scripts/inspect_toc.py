"""Inspect PDF table of contents / bookmarks structure."""
import pymupdf
import sys

pdf_path = r"C:\Medicine study\Harrison's Principles of Internal Medicine - 22nd edition (1).pdf"
doc = pymupdf.open(pdf_path)
toc = doc.get_toc()

print(f"Total pages: {len(doc)}")
print(f"TOC entries: {len(toc)}")
print("\nFirst 60 TOC entries:")
for i, entry in enumerate(toc[:60]):
    level, title, page = entry
    indent = "  " * (level - 1)
    print(f"  {indent}[L{level}] p.{page}: {title}")

if len(toc) > 60:
    print(f"\n... and {len(toc) - 60} more entries")

# Show sample text from a few pages to understand formatting
print("\n=== Sample text from page 1 ===")
print(doc[0].get_text()[:500])
print("\n=== Sample text from page 50 ===")
print(doc[49].get_text()[:500])

doc.close()
