"""Generate structured medical notes from textbook content.

Usage:
    python scripts/generate_note.py "Disease Name" [--specialty "科別"]
    python scripts/generate_note.py "Nephrotic Syndrome"
    python scripts/generate_note.py "高血壓" --specialty "心臟內科"
"""
import argparse
import json
import os
import re
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(SCRIPT_DIR, "..")
CONFIG_DIR = os.path.join(ROOT_DIR, "config")
NOTES_DIR = os.path.join(ROOT_DIR, "docs", "notes")
TEMPLATE_PATH = os.path.join(CONFIG_DIR, "template.json")

sys.path.insert(0, SCRIPT_DIR)
from search import search_and_retrieve

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    TEMPLATE = json.load(f)

SECTION_NAMES = [s["title"] for s in TEMPLATE["sections"]]

SYSTEM_PROMPT = """You are a medical education assistant that creates structured study notes from textbook content.

Your task: given textbook excerpts about a disease/topic, produce a structured note with exactly 10 sections. Write in a mix of English medical terms and Traditional Chinese explanations, matching the style a Taiwanese medical student would use.

OUTPUT FORMAT: Return valid JSON with this structure:
{
  "title": "Disease Name (中文名)",
  "title_en": "Disease Name",
  "title_zh": "中文名",
  "specialty": "科別",
  "sections": [
    {
      "title": "Section Title",
      "content": [blocks...]
    }
  ],
  "related_topics": ["Related Disease 1", "Related Disease 2"]
}

Each section's "content" is an array of blocks. Block types:
- String: plain paragraph text (supports **bold** and *italic*)
- {"type": "callout", "style": "guideline|logic|trap", "text": "..."}
  - guideline: evidence-based guidelines, diagnostic criteria
  - logic: clinical reasoning, pathophysiology connections
  - trap: common exam mistakes, easily confused points
- {"type": "collapsible", "summary": "Title", "text": "detailed content"}
- {"type": "table", "headers": ["Col1","Col2"], "rows": [["a","b"]]}
- {"type": "list", "ordered": false, "items": ["item1","item2"]}
- {"type": "heading", "text": "Subtitle"}
- {"type": "source", "book": "Harrison's 22e", "pages": "123-456"}

RULES:
1. Use all 10 sections in order: Overview/Epidemiology, Etiology/Risk Factors, Pathophysiology, Pathology, Clinical Presentation, Diagnosis, Treatment, Prognosis/Follow-up, Special Populations, High-Yield Exam Points
2. If textbook content doesn't cover a section well, write a brief note and mark it
3. Use callout blocks for important guidelines (📌), clinical logic (💡), and exam traps (⚠️)
4. Put detailed drug dosages, microbe lists, and classification tables in collapsible blocks
5. Keep each section focused and concise - prioritize high-yield content
6. Include source references using source blocks
7. Suggest 3-5 related topics from the SAME specialty for cross-linking
8. Return ONLY valid JSON, no other text"""


def slugify(text):
    text = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    text = re.sub(r'[\s]+', '-', text.strip())
    return text[:60].strip('-').lower() or 'untitled'


def build_prompt(disease_name, search_results, specialty=None):
    """Build the user prompt with search results."""
    context_parts = []
    sources = []
    for r in search_results:
        source = f"{r['book']} - {r['title']}"
        if r['pages']:
            source += f" (p.{r['pages']})"
        sources.append(source)
        context_parts.append(f"=== {source} ===\n{r['content'][:25000]}")

    context = "\n\n".join(context_parts)

    prompt = f"""Generate a structured medical note for: {disease_name}
"""
    if specialty:
        prompt += f"Specialty: {specialty}\n"
    prompt += f"""
The following textbook content is available:
Sources: {', '.join(sources)}

--- TEXTBOOK CONTENT ---
{context}
--- END CONTENT ---

Generate the 10-section structured note as JSON. Focus on the most clinically relevant and exam-relevant content."""

    return prompt, sources


def call_claude_api(system_prompt, user_prompt):
    """Call Claude API to generate the note."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed.")
        print("Install with: pip install anthropic")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        print("Set it with: $env:ANTHROPIC_API_KEY = 'sk-ant-...'")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print("  Calling Claude API...")
    start = time.time()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    elapsed = time.time() - start
    print(f"  API response received ({elapsed:.1f}s)")

    text = response.content[0].text.strip()
    # Extract JSON from response (handle markdown code blocks)
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

    return json.loads(text)


def call_claude_cli(system_prompt, user_prompt):
    """Use Claude Code CLI as fallback when API key is not available."""
    import subprocess
    import tempfile

    prompt_file = os.path.join(tempfile.gettempdir(), "note_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}")

    print("  Note: Using Claude CLI (set ANTHROPIC_API_KEY for direct API).")
    print(f"  Prompt saved to: {prompt_file}")
    print("  Copy the prompt and paste into Claude to generate the note JSON.")
    return None


def update_notes_index(note_id, note_data, specialty):
    """Update the notes/index.json file."""
    index_path = os.path.join(NOTES_DIR, "index.json")

    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = {"specialties": []}

    spec_entry = None
    for s in index["specialties"]:
        if s["name"] == specialty:
            spec_entry = s
            break
    if not spec_entry:
        spec_entry = {"name": specialty, "diseases": []}
        index["specialties"].append(spec_entry)

    existing = [d for d in spec_entry["diseases"] if d["id"] != note_id]
    existing.append({
        "id": note_id,
        "name": note_data.get("title", note_id),
    })
    spec_entry["diseases"] = sorted(existing, key=lambda d: d["name"])

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    return index


def resolve_related_links(note_data):
    """Convert related_topics list to id-based links."""
    related = []
    topics = note_data.get("related_topics", [])
    for topic in topics[:5]:
        related.append({
            "id": slugify(topic),
            "name": topic,
        })
    return related


def generate_note(disease_name, specialty=None, use_api=True):
    """Main note generation pipeline."""
    print(f"\n=== Generating note: {disease_name} ===\n")

    # Step 1: Search textbooks
    print("1. Searching textbooks...")
    results = search_and_retrieve(disease_name, max_results=6, max_chars_per_chapter=25000)
    if not results:
        print("   No relevant content found in textbooks.")
        return None

    print(f"   Found {len(results)} relevant chapters:")
    for r in results:
        print(f"     - [{r['book']}] {r['title']} (relevance: {r['relevance']})")

    # Step 2: Build prompt
    print("\n2. Building prompt...")
    user_prompt, sources = build_prompt(disease_name, results, specialty)
    print(f"   Prompt length: {len(user_prompt):,} chars")

    # Step 3: Generate note via Claude
    print("\n3. Generating note...")
    if use_api and os.environ.get("ANTHROPIC_API_KEY"):
        note_data = call_claude_api(SYSTEM_PROMPT, user_prompt)
    else:
        note_data = call_claude_cli(SYSTEM_PROMPT, user_prompt)
        if note_data is None:
            return None

    # Step 4: Post-process
    note_id = slugify(disease_name)
    note_data["id"] = note_id
    note_data["sources"] = sources
    note_data["generated"] = time.strftime("%Y-%m-%d")
    note_data["related"] = resolve_related_links(note_data)

    if not specialty and note_data.get("specialty"):
        specialty = note_data["specialty"]
    elif not specialty:
        specialty = "Other"

    note_data["specialty"] = specialty

    # Step 5: Save note JSON
    os.makedirs(NOTES_DIR, exist_ok=True)
    note_path = os.path.join(NOTES_DIR, f"{note_id}.json")
    with open(note_path, "w", encoding="utf-8") as f:
        json.dump(note_data, f, ensure_ascii=False, indent=2)
    print(f"\n4. Note saved: {note_path}")

    # Step 6: Update index
    index = update_notes_index(note_id, note_data, specialty)
    total = sum(len(s["diseases"]) for s in index["specialties"])
    print(f"5. Index updated: {total} total notes across {len(index['specialties'])} specialties")

    print(f"\n=== Done! View at: index.html#{note_id} ===")
    return note_data


def main():
    parser = argparse.ArgumentParser(description="Generate structured medical notes")
    parser.add_argument("disease", help="Disease or topic name")
    parser.add_argument("--specialty", "-s", help="Specialty (科別)")
    parser.add_argument("--no-api", action="store_true", help="Skip API call, just save prompt")
    args = parser.parse_args()

    generate_note(args.disease, args.specialty, use_api=not args.no_api)


if __name__ == "__main__":
    main()
