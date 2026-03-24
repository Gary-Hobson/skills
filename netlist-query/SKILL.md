---
name: netlist-query
description: Parse Allegro/OrCAD exported PST netlist files and query circuit connections. Use when the user needs to view schematic netlists, query component pin connections, find peripheral circuits of a chip, trace signal paths, or see which chips are used — any hardware design connectivity questions. Trigger even when the user just mentions "where does this chip connect to", "IMU peripheral circuit", "check netlist", "which ICs are used", "what pin does this signal go to". Supports Allegro PST netlist parsing, component/net/peripheral circuit queries, and cross-session memory caching.
user-invocable: true
---

# Netlist Query Skill

Parse Cadence Allegro / OrCAD exported PST netlist files and efficiently query component information and net connections via structured JSON.

## Quick Start

`<skill_dir>` refers to the absolute path of the directory containing this SKILL.md.

```bash
# Parse netlist (one-time, generates JSON + memory)
python3 <skill_dir>/scripts/parse_netlist.py <allegro_dir>

# Command-line query
python3 <skill_dir>/scripts/query_netlist.py <design_name> <command> [args]

# Or query JSON directly with jq / python
cat ~/.cache/skills/netlist-query/<design_name>/netlist.json | jq '.category_index.ic'
```

Prerequisite: requires Allegro-exported `pstchip.dat`, `pstxprt.dat`, and `pstxnet.dat` files.

## Storage Structure

All parsed netlists are stored in `~/.cache/skills/netlist-query/`:

```
~/.cache/skills/netlist-query/
  ${design_name}/
    netlist.json       # Complete structured netlist data (with version, date)
    memory.md          # Query cache (previously queried circuit summaries)
    raw/               # Original PST netlist file backups
      pstchip.dat
      pstxprt.dat
      pstxnet.dat
      netlist.log      # (if present)
```

## Netlist Parsing

When the user provides a directory containing PST files:

```bash
python3 <skill_dir>/scripts/parse_netlist.py <allegro_directory> [--name <design_name>] [--version <version>]
```

Design name defaults to the `ROOT_DRAWING` attribute from `pstxprt.dat`, or the directory name.
Version defaults to the `POST_TIME` from `pstxprt.dat`, or the current date.
Original netlist files are automatically backed up to the `raw/` subdirectory.

## JSON Structure

```json
{
  "_meta": {
    "design_name": "...",
    "version": "Aug  5 2023 23:58:48",
    "parsed_at": "2026-03-18 16:30:00",
    "post_time": "Aug  5 2023 23:58:48",
    "pstwriter": "17.4.0 d001 on Mar-18-2026 at 14:02:37",
    "stats": { "total_components": N, "total_nets": N, "ics": N, ... }
  },
  "category_index": {
    "ic": {
      "total": 47, "unique_parts": 31,
      "parts": [
        {
          "part_name": "U_LSM6DSV16X",
          "value": "U_LSM6DSV16X",
          "footprint": "...",
          "count": 1,
          "refdes_list": ["U1700"]
        }
      ]
    },
    "resistor": { ... },
    "capacitor": { ... },
    "connector": { ... }
  },
  "components": {
    "U1700": {
      "refdes": "U1700",
      "part_name": "U_LSM6DSV16X",
      "value": "U_LSM6DSV16X",
      "footprint": "...",
      "category": "ic",
      "schematic_page": "page9",
      "pins": {
        "1": { "name": "SDO/SA0", "number": "1", "use": "UNSPEC", "net": "SPI_IMUTOAA_MISO" },
        "12": { "name": "CS", "number": "12", "use": "UNSPEC", "net": "SPI_IMUTOAA_CS_N" }
      }
    }
  },
  "nets": {
    "SPI_IMUTOAA_MISO": [
      { "refdes": "U1700", "pin_number": "1", "pin_name": "SDO/SA0" },
      { "refdes": "J2839", "pin_number": "53", "pin_name": "53" },
      { "refdes": "TP66", "pin_number": "1", "pin_name": "1" }
    ]
  }
}
```

## Query Flow

Priority: **Memory direct-lookup → category_index overview → JSON precise query → Update Memory**

The design logic behind this priority: memory caches previously queried circuit connection summaries without re-parsing; category_index provides a quick overview; full JSON data provides precise pin-level queries.

### Step 0: Identify Target Design

```bash
ls ~/.cache/skills/netlist-query/
```

### Step 1: Read Memory

Always read memory before each query — previously queried circuit info can be reused directly:

```
Read → ~/.cache/skills/netlist-query/<design_name>/memory.md
```

- **Hit**: memory has target circuit summary → use directly
- **Miss**: continue to Step 2

### Step 2: Quick Overview (category_index)

For overview questions like "which chips are used" or "how many capacitors", just read `category_index`:

```bash
# Command-line
python3 <skill_dir>/scripts/query_netlist.py <design_name> list-ic
python3 <skill_dir>/scripts/query_netlist.py <design_name> list-category connector

# Or with jq
jq '.category_index.ic.parts[] | {part_name, count, refdes_list}' netlist.json
```

### Step 3: Precise Query

Choose the appropriate command based on query type:

| Query Type | Command | Example |
|-----------|---------|---------|
| Component info + pins | `component <refdes>` | `component U1700` |
| All nodes on a net | `net <net_name>` | `net SPI_IMUTOAA_MISO` |
| IC peripheral circuit | `peripheral <refdes>` | `peripheral U1700` |
| Keyword search | `search <keyword>` | `search IMU` |
| Pin mapping table | `pin-map <refdes>` | `pin-map U1700` |
| List all ICs | `list-ic` | |
| List by category | `list-category <cat>` | `list-category connector` |

**Direct Python query (no script needed, suitable for complex queries):**

```python
import json, os
with open(os.path.expanduser('~/.cache/skills/netlist-query/<design_name>/netlist.json')) as f:
    nl = json.load(f)

# Query all pin connections for a component
comp = nl["components"]["U1700"]
for pin_num, pin in comp["pins"].items():
    print(f'{pin["name"]}: {pin.get("net", "N/C")}')

# Query which components are connected to a net
for node in nl["nets"]["SPI_IMUTOAA_MISO"]:
    print(f'{node["refdes"]}.{node["pin_name"]}')

# Find all peripheral components for an IC
refdes = "U1700"
comp = nl["components"][refdes]
for pin in comp["pins"].values():
    net = pin.get("net")
    if net and net not in ("GND", "VCC"):
        for node in nl["nets"].get(net, []):
            if node["refdes"] != refdes:
                peer = nl["components"].get(node["refdes"], {})
                print(f'{pin["name"]} --[{net}]--> {node["refdes"]} ({peer.get("part_name","?")})')
```

### Step 4: Update Memory

After finding new information, update memory so subsequent queries for the same circuit don't need re-parsing:

```markdown
## U1700 LSM6DSV16X (IMU) - Peripheral Circuit

### SPI Bus → J2839 (B2B Connector)
- Pin 1  SDO/SA0 → SPI_IMUTOAA_MISO → J2839.53, TP66
- Pin 14 SDA     → SPI_IMUTOAA_MOSI → J2839.54, TP65
- Pin 13 SCL     → SPI_IMUTOAA_SCLK → J2839.55, TP64
- Pin 12 CS      → SPI_IMUTOAA_CS_N → J2839.56, TP63

### Interrupts
- Pin 4  INT1    → IMU_INT_AA       → J2839.52, TP67

### Power
- Pin 5  VDD_IO  → VREG_SYSTEM_1P8
- Pin 8  VDD     → VREG_SYSTEM_1P8
- Pin 6,7 GND    → GND
```

Use the Edit tool to append to the end of memory.md.

## Common Query Patterns

| User Question | Query Method |
|--------------|-------------|
| "Which chips are used" | `list-ic` or read `category_index.ic` |
| "Where does the IMU connect" | `search IMU` → `peripheral U1700` |
| "What's connected to this signal" | `net <signal_name>` |
| "Pin table for this chip" | `pin-map <refdes>` |
| "Which components on this power rail" | `net VREG_SYSTEM_1P8` |
| "How are two components connected" | query `component` for each, find common nets |
| "How many LDOs on the board" | `search SGM2045` or filter by category |

## Output Format Requirements

Query results should clearly present connection relationships, including:

1. **Component identifier**: RefDes + part name (e.g., `U1700 [LSM6DSV16X]`)
2. **Pin mapping**: Pin number + pin name + connected net name
3. **Connection peers**: all components and pins on the other end of the net
4. **Schematic location**: schematic_page info (e.g., `page9`)

Output example:
```
U1700 [LSM6DSV16X] (IMU, page9)
  Pin 13 (SCL) → SPI_IMUTOAA_SCLK → J2839.55 [B2B connector], TP64 [test point]
```

## Important Rules

- **Memory first** — reading memory is the first step of every query; previously queried circuit info can be reused directly
- **Update memory after queries** — append to memory.md after each new circuit info lookup from JSON
- **Avoid full-file loading** — netlist.json can be large (>500KB); prefer using the script or jq for queries, don't read the entire file into context
- **category_index for overviews** — for overview questions ("which ICs"), query category_index directly instead of traversing components
- **Filter GND/VCC/NC** — when querying peripheral circuits, automatically filter power, ground, NC nets, and large bus nets with >20 nodes; focus on signal connections
- **Case-insensitive** — searches automatically ignore case

## Skill Chaining

After identifying a chip part number from the netlist, use `lcsc-datasheet` skill to search LCSC and download its datasheet, then use `datasheet` skill to convert and query the PDF content.
