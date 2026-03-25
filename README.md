# Skills

Claude Code skills for hardware development.

| Skill | Description |
|-------|-------------|
| [lcsc-datasheet](lcsc-datasheet/) | Search components on LCSC and download datasheets |
| [datasheet](datasheet/) | Convert PDF datasheets to Markdown for querying |
| [netlist-query](netlist-query/) | Parse Allegro/OrCAD netlists and query circuit connections |

## Installation

### 1. Clone

```bash
git clone https://github.com/Gary-Hobson/skills.git
```

### 2. Copy skills you need into your project or user skills directory

```bash
# Project-level (only this project)
cp -r skills/lcsc-datasheet .claude/skills/

# User-level (all projects)
cp -r skills/lcsc-datasheet ~/.claude/skills/
```

### 3. Install dependencies

**lcsc-datasheet** — no setup needed (`requests` optional, falls back to `curl`)

**datasheet** — requires `marker-pdf`:

```bash
pip install marker-pdf
# Run once to download models (~1-2GB):
marker_single datasheet/references/sample.pdf --output_dir /tmp/test --output_format markdown
```

**netlist-query** — no setup needed (stdlib only)

## How They Work Together

```
netlist-query                lcsc-datasheet              datasheet
(find chip on board)  →  (search & download PDF)  →  (convert & query)

"What ICs are on        "Download the AW36514       "What's the I2C
 the board?"        datasheet"                   address?"
```
