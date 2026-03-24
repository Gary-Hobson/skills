# marker-pdf Installation Guide

The datasheet skill depends on [marker-pdf](https://github.com/datalab-to/marker) to convert PDFs to Markdown.

## Installation

```bash
pip install marker-pdf
```

Models are automatically downloaded on first run (~1-2GB), requires network connection.

## Usage

Convert a single PDF:

```bash
marker_single input.pdf --output_dir ./output --output_format markdown
```

Output directory structure:

```
output/
  input/
    input.md          # Markdown body
    input_meta.json   # Metadata (TOC, page info)
    images/           # Extracted images
```

The datasheet skill wraps the above command — just use:

```bash
python .claude/skills/datasheet/scripts/datasheet.py input.pdf
```

## Verification

```bash
marker_single --help
```
