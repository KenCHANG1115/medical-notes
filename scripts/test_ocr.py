"""Quick OCR test on a few sample pages from First Choice."""
import pymupdf
import pytesseract
import json
import os
from PIL import Image
import io
import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "books.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

pytesseract.pytesseract.tesseract_cmd = config["tesseract_cmd"]
os.environ["TESSDATA_PREFIX"] = config["tessdata_dir"]

pdf_path = os.path.join(config["library_path"], "醫學(三)第1冊.pdf")
doc = pymupdf.open(pdf_path)

test_pages = [4, 10, 50, 100]

for p in test_pages:
    if p >= len(doc):
        continue
    page = doc[p]

    start = time.time()
    mat = pymupdf.Matrix(300 / 72, 300 / 72)
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(img, lang="chi_tra+eng")
    elapsed = time.time() - start

    print(f"=== Page {p+1} ({elapsed:.1f}s) ===")
    print(text[:400])
    print(f"[{len(text)} chars total]")
    print()

doc.close()
