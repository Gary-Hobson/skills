---
name: datasheet
description: Convert PDF datasheets to Markdown and efficiently query technical content. Use this skill whenever the user needs to look up chip manuals, datasheets, technical reference manuals, user guides, or any PDF technical documents. Trigger even when the user just mentions "check registers for this chip", "look at the datasheet", "how to configure this sensor". Supports PDF-to-Markdown conversion, bookmark index navigation, layered search, and cross-session memory caching.
user-invocable: true
---

# Datasheet Query Skill

Convert PDF technical documents to searchable Markdown and efficiently locate content via a three-level index (memory → bookmarks → grep).

## Quick Start

```bash
# Convert PDF (auto-generates bookmark index)
python .claude/skills/datasheet/scripts/datasheet.py <PDF_path>

# Query (by priority)
# 1. Read memory → 2. Search bookmarks → 3. Grep document → 4. Read content → 5. Update memory
```

Prerequisite: requires marker-pdf (`pip install marker-pdf`). See `references/setup.md` for detailed installation instructions.

## Storage Structure

All documents are stored in `~/.cache/skills/datasheet/`:

```
~/.cache/skills/datasheet/
  ${doc_name}/
    ${doc_name}.md              # Markdown document
    ${doc_name}_meta.json       # Metadata (TOC, page stats)
    bookmarks.tsv               # Bookmark index (title\tpage)
    memory.md                   # Query cache (line number index)
```

## Helper Script

Unified script `scripts/datasheet.py`: pass the PDF path directly, it auto-completes conversion + bookmark generation.

```bash
python .claude/skills/datasheet/scripts/datasheet.py <pdf_path>
```

Large PDFs (>500 pages) take a while to convert — use `run_in_background`.

## PDF Conversion Flow

When the user provides a PDF file, run directly:

```bash
python .claude/skills/datasheet/scripts/datasheet.py <PDF_file_path>
```

## Output Format Requirements

Every query result must include source references so the user can trace back and verify. Sources have two parts:

1. **Terminal-clickable file link**: `<absolute_path_to_doc.md>:<line_number>` — click to jump directly
2. **PDF original location**: be as detailed as possible, including the full section hierarchy path and page number, so the user can locate it directly in the original PDF

The detail level of PDF location matters — when the user has a printed manual or PDF reader, they need to know "which table in which subsection of which chapter", not just a vague section number. Find the nearest parent section from bookmarks.tsv and compose the full path.

Output example:
```
IQ_NO_LOAD typical 60 nA (VOUT=1.8V, no load)
  → ~/.cache/skills/datasheet/tps62840/tps62840.md:245
    PDF: 7 Specifications > 7.5 Electrical Characteristics > Table: SUPPLY (p.7)
```

Source column in tables:
```
| Parameter | Value | Source |
|-----------|-------|--------|
| IQ_NO_LOAD | 60 nA | [:245](~/.cache/.../tps62840.md:245) 7 > 7.5 Electrical Characteristics > SUPPLY (p.7) |
```

The reason for this: users frequently need to cross-check data against the original PDF. Terminal-clickable links jump to the Markdown line, while detailed PDF section path + page number lets the user go directly to the corresponding position in the original document.

## Query Flow

Priority: **Memory direct-jump → Bookmark search → Document Grep → Read expand**

The design logic behind this priority: memory caches line numbers of previously read content with zero search overhead; bookmarks map the document TOC for the most precise scope; grep full-text search is most flexible but slowest. This order locates target content fastest while avoiding loading the entire document into context (large manuals can be tens of thousands of lines, which would exhaust the context window).

### Step 0: Identify Target Document

When multiple documents exist, first confirm which one to query:

```bash
ls ~/.cache/skills/datasheet/
```

When the user doesn't specify, infer the most relevant document based on query content.

### Step 1: Read Memory Index

Always read memory before each query — previously queried content already has line number indexes for direct jumping:

```
Read → ~/.cache/skills/datasheet/<doc_name>/memory.md
```

- **Hit**: memory has target line number → directly `Read(offset=line_number, limit=200)` to jump
- **Miss**: continue to Step 2

### Step 2: Bookmark Search

Search bookmarks for keywords to find relevant section titles:

```
Grep pattern="<keyword>" path=".../<doc_name>/bookmarks.tsv" -i=True output_mode="content"
```

Bookmark format: `<section_title>\t<page_number>`

Record matched section titles and page numbers — you'll need them for output and memory updates.

### Step 3: Locate Document Line Number

Use the **exact title** found in bookmarks to search precisely in the Markdown document:

```
Grep pattern="^## <bookmark_title>" path=".../<doc_name>/<doc_name>.md" -n=True output_mode="content"
```

Search tips:
- First use `output_mode="count"` to check match count
- 0 matches → try partial title or remove `^`
- 1-5 matches → ideal, read directly
- >20 matches → too broad, use a more precise title

### Step 4: Read Content

```
Read → ~/.cache/skills/datasheet/<doc_name>/<doc_name>.md  offset=<line_number> limit=200
```

If more content is needed, increase offset to continue reading downward.

### Step 5: Update Memory

After reading new content, update the memory index. This way the next query for the same content skips the search — direct line number jump:

```markdown
## <Section/Topic Name> (L<start_line>-<end_line>, §<PDF_section_number> PDF p.<page>)

### <Subtitle> (L<line_number>)
- L<line_number>: <key content summary>
- <important details, register definitions, parameter values, etc.>
```

PDF section numbers and page numbers come from bookmarks.tsv (format: `title\tpage`). Record matched section info during the bookmark search phase and include it when writing to memory.

Use the Edit tool to append to the end of memory.md.

## Common Query Patterns

| Query Type | Bookmark Search Keywords |
|-----------|------------------------|
| Chip/module features | Features, Introduction, Overview |
| Register definitions | Register, or search register name directly |
| Pins/interfaces | Pin, Interface, Signal |
| Electrical parameters | Electrical, Specification, Parameter |
| Timing/waveforms | Timing, Waveform |
| Programming/configuration | Programming, Configuration, Initialization |

## Cross-Document Search

When unsure which document contains the content, search all bookmarks:

```
Grep pattern="<keyword>" path="~/.cache/skills/datasheet/" glob="*/bookmarks.tsv" -i=True
```

## Important Rules

- **Memory first** — reading memory is the first step of every query, because it provides zero-overhead line number direct jumping
- **Update memory after reading** — append index after each new content read from the document; this is key to the memory system's sustained acceleration
- **Avoid full-file loading** — large manuals have tens of thousands of lines; use Grep to locate line numbers then Read local content
- **Progressive expansion** — read 200 lines first, continue if needed, avoid reading too much at once to conserve context
- **Naming convention** — when converting datasheets downloaded by `lcsc-datasheet` skill, the downloaded filename may contain the full MPN with suffixes (e.g., `MAX31875R0TZS_T_datasheet.pdf`). The converted cache directory name is derived from the filename, so use a short chip family name when possible to keep cache paths clean and reusable across MPN variants
