"""Inspect First Choice PDF bookmarks."""
import pymupdf
import os

base = r"C:\Medicine study"
files = [
    "醫學(三)第1冊.pdf",
    "醫學(三)第2冊原稿頁碼有錯336起,誤為374起.pdf",
    "醫學(三)第3冊.pdf",
    "醫學(三)第4冊.pdf",
]

for fn in files:
    path = os.path.join(base, fn)
    doc = pymupdf.open(path)
    toc = doc.get_toc()
    print(f"{fn}: {len(doc)} pages, {len(toc)} TOC entries")
    for entry in toc[:10]:
        level, title, page = entry
        indent = "  " * level
        print(f"  {indent}[L{level}] p.{page}: {title}")
    if len(toc) > 10:
        print(f"  ... and {len(toc) - 10} more")
    doc.close()
    print()
