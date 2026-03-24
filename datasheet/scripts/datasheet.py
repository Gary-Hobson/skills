#!/usr/bin/env python3
"""PDF datasheet converter: PDF to Markdown + bookmark index generation.

Usage:
  datasheet.py <pdf_path>

Output directory: ~/.cache/skills/datasheet/<doc_name>/

Prerequisite: requires marker-pdf (pip install marker-pdf)
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path.home() / ".cache" / "skills" / "datasheet"


def main():
    if len(sys.argv) != 2 or sys.argv[1].startswith("-"):
        print(f"Usage: {sys.argv[0]} <pdf_path>")
        sys.exit(1)

    pdf = Path(sys.argv[1]).resolve()
    if not pdf.is_file():
        print(f"Error: file not found: {pdf}", file=sys.stderr)
        sys.exit(1)

    marker = shutil.which("marker_single")
    if not marker:
        print("Error: marker_single not installed", file=sys.stderr)
        print("Install manually: pip install marker-pdf", file=sys.stderr)
        print("See: .claude/skills/datasheet/references/setup.md", file=sys.stderr)
        sys.exit(1)

    doc_name = pdf.stem
    doc_dir = BASE_DIR / doc_name

    print("=" * 42)
    print(f"Input: {pdf}")
    print(f"Output: {doc_dir}/")
    print("=" * 42)

    BASE_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            marker,
            str(pdf),
            "--output_dir",
            str(BASE_DIR),
            "--output_format",
            "markdown",
        ],
        check=True,
    )

    md_file = doc_dir / f"{doc_name}.md"
    if not md_file.is_file():
        print(f"Error: Markdown file not generated: {md_file}", file=sys.stderr)
        sys.exit(1)

    # memory file
    memory_file = doc_dir / "memory.md"
    if not memory_file.is_file():
        memory_file.write_text(
            f"# {doc_name} - Content Index\n\n"
            f"> This file records line positions of previously read content from `{md_file}`,\n"
            "> for quick lookup, avoiding repeated searches.\n\n"
            "(no records yet)\n",
            encoding="utf-8",
        )

    # bookmark index
    meta_file = doc_dir / f"{doc_name}_meta.json"
    bookmarks_file = doc_dir / "bookmarks.tsv"
    bm_count = 0
    if meta_file.is_file():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        toc = meta.get("table_of_contents", [])
        with bookmarks_file.open("w", encoding="utf-8") as out:
            for item in toc:
                title = item.get("title", "").strip()
                if not title:
                    continue
                page = item.get("page_id", 0) + 1
                out.write(f"{title}\t{page}\n")
                bm_count += 1

    # summary
    line_count = sum(1 for _ in md_file.open(encoding="utf-8"))
    size_kb = md_file.stat().st_size / 1024
    print("=" * 42)
    print(f"Markdown : {md_file}  ({size_kb:.0f}K, {line_count} lines)")
    if bm_count:
        print(f"Bookmarks: {bookmarks_file}  ({bm_count} entries)")
        lines = bookmarks_file.read_text(encoding="utf-8").splitlines()
        print(f"\nFirst 20 bookmarks:\n{'-' * 40}")
        for line in lines[:20]:
            print(line)
        if len(lines) > 20:
            print(f"... (total {len(lines)} entries)")
    print(f"Memory   : {memory_file}")


if __name__ == "__main__":
    main()
