"""Process First Choice txt files into structured chapters."""
import json
import os
import re

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "books.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

OUTPUT_BASE = os.path.join(config["output_path"], "first-choice")

VOLUME_INFO = [
    {
        "txt": "醫學(三)第1冊.txt",
        "id": "vol1",
        "specialties": ["心臟內科", "胸腔內科"],
    },
    {
        "txt": "醫學(三)第2冊原稿頁碼有錯336起,誤為374起.txt",
        "id": "vol2",
        "specialties": ["腸胃內科", "肝膽內科", "新陳代謝科"],
    },
    {
        "txt": "醫學(三)第3冊.txt",
        "id": "vol3",
        "specialties": ["腎臟內科", "感染科"],
    },
    {
        "txt": "醫學(三)第4冊.txt",
        "id": "vol4",
        "specialties": ["免疫風濕科", "血液科", "腫瘤科", "家庭醫學科"],
    },
]

TOPIC_MARKERS = list("甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥")
NUM_WORDS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def slugify(text):
    text = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    text = re.sub(r'[\s]+', '-', text.strip())
    return text[:60].strip('-') or 'untitled'


def parse_pages(content):
    parts = re.split(r'---\s*Page\s+(\d+)\s*---', content)
    pages = []
    for i in range(1, len(parts), 2):
        page_num = int(parts[i])
        text = parts[i + 1] if i + 1 < len(parts) else ""
        pages.append((page_num, text))
    return pages


def find_specialty_boundaries(pages, known_specialties, min_content_page=10):
    """Find where each specialty's content starts.

    Strategy: use 第X篇 markers (last occurrence of each), then also search
    for standalone specialty name lines (e.g. "感染科") as fallback for
    sections that lack a 第X篇 marker.
    """
    pian_pattern = re.compile(r'第([一二三四五六七八九十]+)篇')
    last_seen = {}

    for i, (pnum, text) in enumerate(pages):
        for line in text.split('\n'):
            m = pian_pattern.search(line)
            if m:
                pian_num_str = m.group(1)
                pian_num = NUM_WORDS.get(pian_num_str, 0)
                has_stats = bool(re.search(r'\d+\s*\|\s*\d+', line))
                if has_stats:
                    continue
                last_seen[pian_num] = {
                    "pian_num": pian_num,
                    "page_idx": i,
                    "page_num": pnum,
                }

    boundaries = sorted(last_seen.values(), key=lambda x: x["pian_num"])

    # Check which specialties are missing and search for standalone name lines
    found_specs = set()
    for b in boundaries:
        idx = b["pian_num"] - 1
        if idx < len(known_specialties):
            found_specs.add(known_specialties[idx])

    for spec_idx, spec_name in enumerate(known_specialties):
        if spec_name in found_specs:
            continue
        # Search for a standalone line that is just the specialty name
        for i, (pnum, text) in enumerate(pages):
            if pnum < min_content_page:
                continue
            for line in text.split('\n'):
                stripped = line.strip()
                if stripped == spec_name or stripped.startswith(spec_name + '\n'):
                    boundaries.append({
                        "pian_num": spec_idx + 1,
                        "page_idx": i,
                        "page_num": pnum,
                    })
                    found_specs.add(spec_name)
                    break
            if spec_name in found_specs:
                break

    boundaries = sorted(boundaries, key=lambda x: x["page_idx"])

    sections = []
    for j, b in enumerate(boundaries):
        spec_idx = b["pian_num"] - 1
        spec_name = known_specialties[spec_idx] if spec_idx < len(known_specialties) else f"section-{b['pian_num']}"
        end_idx = boundaries[j + 1]["page_idx"] if j + 1 < len(boundaries) else len(pages)
        if any(s["name"] == spec_name for s in sections):
            continue
        sections.append({
            "name": spec_name,
            "start_idx": b["page_idx"],
            "end_idx": end_idx,
            "start_page": b["page_num"],
        })

    if not sections and pages:
        sections.append({
            "name": known_specialties[0] if known_specialties else "content",
            "start_idx": 0,
            "end_idx": len(pages),
            "start_page": pages[0][0],
        })

    return sections


def detect_topics(pages, start_idx, end_idx):
    """Detect 甲、乙、丙、... topic boundaries within a section."""
    topics = []
    pattern = re.compile(
        r'^(' + '|'.join(re.escape(m) for m in TOPIC_MARKERS) + r')[、,.\s]+([一-鿿\w\s\(\)（）,，、]+)',
        re.MULTILINE
    )

    for i in range(start_idx, end_idx):
        pnum, text = pages[i]
        for m in pattern.finditer(text):
            marker = m.group(1)
            topic_name = m.group(2).strip()
            topic_name = re.sub(r'[\d\s.,、]+$', '', topic_name).strip()
            topic_name = re.sub(r'\s+', '', topic_name)
            if len(topic_name) < 2 or len(topic_name) > 30:
                continue
            marker_idx = TOPIC_MARKERS.index(marker) if marker in TOPIC_MARKERS else -1
            if topics and marker_idx <= (TOPIC_MARKERS.index(topics[-1]["marker"]) if topics[-1]["marker"] in TOPIC_MARKERS else -1):
                continue
            if topics:
                topics[-1]["end_idx"] = i
            topics.append({
                "marker": marker,
                "name": topic_name,
                "start_idx": i,
                "start_page": pnum,
                "end_idx": end_idx,
            })

    if not topics:
        topics.append({
            "marker": "",
            "name": "content",
            "start_idx": start_idx,
            "start_page": pages[start_idx][0] if start_idx < len(pages) else 0,
            "end_idx": end_idx,
        })

    return topics


def extract_topic_text(pages, start_idx, end_idx):
    texts = []
    start_page = pages[start_idx][0] if start_idx < len(pages) else 0
    end_page = pages[min(end_idx, len(pages)) - 1][0] if end_idx > 0 else 0
    for i in range(start_idx, min(end_idx, len(pages))):
        pnum, text = pages[i]
        text = text.strip()
        if text:
            texts.append(f"<!-- page:{pnum} -->\n{text}")
    return "\n\n".join(texts), start_page, end_page


def process_volume(vol_info, global_idx):
    txt_path = os.path.join(config["library_path"], vol_info["txt"])
    if not os.path.exists(txt_path):
        print(f"SKIP: {vol_info['txt']} not found")
        return [], global_idx

    print(f"\nProcessing: {vol_info['txt']}")
    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read()

    pages = parse_pages(content)
    print(f"  Pages: {len(pages)}")

    sections = find_specialty_boundaries(pages, vol_info["specialties"])
    print(f"  Specialties: {[s['name'] for s in sections]}")

    manifest_entries = []

    for sec in sections:
        specialty = sec["name"]
        specialty_slug = slugify(specialty)
        spec_dir = os.path.join(OUTPUT_BASE, specialty_slug)
        os.makedirs(spec_dir, exist_ok=True)

        topics = detect_topics(pages, sec["start_idx"], sec["end_idx"])
        print(f"    {specialty}: {len(topics)} topics")

        for topic in topics:
            global_idx += 1
            text, sp, ep = extract_topic_text(pages, topic["start_idx"], topic["end_idx"])

            marker_part = f"{topic['marker']}-" if topic['marker'] else ""
            filename = f"{global_idx:03d}-{marker_part}{slugify(topic['name'])}.md"
            filepath = os.path.join(spec_dir, filename)

            header = f"{topic['marker']}、{topic['name']}" if topic['marker'] else topic['name']
            frontmatter = (
                f"---\n"
                f'book: "First Choice 醫學(三) 2025"\n'
                f'volume: "{vol_info["id"]}"\n'
                f'specialty: "{specialty}"\n'
                f'topic: "{header}"\n'
                f'pages: "{sp}-{ep}"\n'
                f"---\n\n"
                f"# {header}\n\n"
            )

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(frontmatter + text)

            manifest_entries.append({
                "index": global_idx,
                "volume": vol_info["id"],
                "specialty": specialty,
                "topic": header,
                "pages": f"{sp}-{ep}",
                "file": os.path.relpath(filepath, OUTPUT_BASE),
                "char_count": len(text),
            })

    return manifest_entries, global_idx


def main():
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    all_entries = []
    idx = 0

    for vol in VOLUME_INFO:
        entries, idx = process_volume(vol, idx)
        all_entries.extend(entries)

    manifest_path = os.path.join(OUTPUT_BASE, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    total_chars = sum(e["char_count"] for e in all_entries)
    print(f"\nDone! {len(all_entries)} topics extracted")
    print(f"Total characters: {total_chars:,}")
    print(f"Manifest: {manifest_path}")

    print("\n=== By Specialty ===")
    by_spec = {}
    for e in all_entries:
        by_spec.setdefault(e["specialty"], []).append(e)
    for spec, items in by_spec.items():
        chars = sum(i["char_count"] for i in items)
        print(f"  {spec}: {len(items)} topics, {chars:,} chars")


if __name__ == "__main__":
    main()
