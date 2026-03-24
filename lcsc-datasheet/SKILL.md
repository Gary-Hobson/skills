---
name: lcsc-datasheet
description: Search electronic components on LCSC/JLCPCB and download datasheets using JLCSearch API. Use this skill whenever the user mentions LCSC, JLCPCB, component search, datasheet download, find chip, or wants to look up any electronic component by part number, specifications, or category - even if they don't explicitly say "LCSC". Also trigger when users ask about resistors, capacitors, LDOs, MOSFETs, MCUs, LEDs, connectors, or any electronic part sourcing.
user-invocable: true
---

# LCSC Component Search & Datasheet Download

Search electronic components on LCSC via the JLCSearch public API and download datasheets. No API key required.

## How to search — two approaches

### Approach A: Use the bundled lcsc.py script (recommended when Python + requests is available)

The script is at `scripts/lcsc.py` relative to this skill directory. Locate it dynamically:

```bash
# Find the script path (works regardless of install location)
LCSC="$(dirname "$(find ~/.agents ~/.claude -name lcsc.py -path '*/lcsc-datasheet/scripts/*' 2>/dev/null | head -1)")/lcsc.py"

# Or if you know the skill directory:
LCSC="<skill-dir>/scripts/lcsc.py"

python3 "$LCSC" search BQ27421              # Search by MPN
python3 "$LCSC" resistor 10k 0603           # 10kΩ 0603 resistor
python3 "$LCSC" capacitor 100nF 0805        # 100nF 0805 capacitor
python3 "$LCSC" ldo 3.3 SOT-23             # 3.3V LDO
python3 "$LCSC" mcu --core ARM --flash 64   # ARM MCU, >=64KB flash
python3 "$LCSC" mosfet --vds 30 --package SOT-23
python3 "$LCSC" diode --type schottky
python3 "$LCSC" led --color red --package 0603
python3 "$LCSC" connector header --pitch 2.54 --pins 40
python3 "$LCSC" info C139621               # Part details
python3 "$LCSC" datasheet C139621          # Download datasheet PDF
python3 "$LCSC" datasheet C139621 -o ./pdf # Download to directory
```

Requires: Python 3.10+, `requests` (`pip install requests`).

### Approach B: Use curl directly (works everywhere, no dependencies)

When Python or `requests` is not available, call the JLCSearch API with curl:

```bash
# Search by MPN / keyword
curl -s "https://jlcsearch.tscircuit.com/api/search?q=BQ27421&limit=10"

# Search 10kΩ 0603 resistor
curl -s "https://jlcsearch.tscircuit.com/resistors/list.json?resistance=10000&package=0603&limit=10"

# Search 100nF 0805 capacitor
curl -s "https://jlcsearch.tscircuit.com/capacitors/list.json?capacitance=1e-7&package=0805&limit=10"

# Search 3.3V LDO in SOT-23
curl -s "https://jlcsearch.tscircuit.com/ldos/list.json?output_voltage=3.3&package=SOT-23&limit=10"

# MCU: ARM core, >=64KB flash
curl -s "https://jlcsearch.tscircuit.com/microcontrollers/list.json?core=ARM&flash_min=64&limit=10"

# MOSFET: Vds>=30V, SOT-23
curl -s "https://jlcsearch.tscircuit.com/mosfets/list.json?drain_source_voltage_min=30&package=SOT-23&limit=10"
```

Parse JSON with `jq` if available, otherwise pipe to `python3 -m json.tool`.

## JLCSearch API Reference

Base URL: `https://jlcsearch.tscircuit.com`
No authentication. All endpoints return JSON. Max 100 results per request.

### Generic Search

| Endpoint | Key Params |
|----------|-----------|
| `GET /api/search` | `q` (keyword), `limit`, `package`, `is_basic`, `is_preferred` |
| `GET /components/list.json` | `search`, `subcategory_name`, `package`, `is_basic`, `is_preferred` |

### Category Endpoints

| Category | Endpoint | Params |
|----------|----------|--------|
| Resistors | `/resistors/list.json` | `resistance` (ohms), `is_basic` |
| Capacitors | `/capacitors/list.json` | `capacitance` (farads), `is_basic` |
| LDOs | `/ldos/list.json` | `output_voltage`, `output_type` |
| Voltage Regulators | `/voltage_regulators/list.json` | `output_voltage`, `output_type`, `is_ldo` |
| Boost Converters | `/boost_converters/list.json` | `input_voltage`, `output_voltage`, `output_current` |
| Buck-Boost | `/buck_boost_converters/list.json` | `input_voltage`, `output_voltage`, `output_current` |
| MOSFETs | `/mosfets/list.json` | `drain_source_voltage_min/max`, `continuous_drain_current_min/max`, `mounting_style` |
| BJTs | `/bjt_transistors/list.json` | `current_gain_min`, `collector_current_min`, `mfr`, `search` |
| Diodes | `/diodes/list.json` | `diode_type` |
| LEDs | `/leds/list.json` | `color` |
| LED Drivers | `/led_drivers/list.json` | `supply_voltage_min/max`, `output_current_min/max`, `channel_count` |
| MCUs | `/microcontrollers/list.json` | `core`, `flash_min`, `ram_min`, `interface` |
| ARM Processors | `/arm_processors/list.json` | `flash_min`, `ram_min`, `interface` |
| RISC-V | `/risc_v_processors/list.json` | `flash_min`, `ram_min`, `interface` |
| FPGAs | `/fpgas/list.json` | `type`, `logic_elements_min`, `embedded_ram_min_bits` |
| ADCs | `/adcs/list.json` | `resolution`, `interface`, `is_differential`, `channels` |
| DACs | `/dacs/list.json` | `resolution`, `interface`, `channels` |
| IO Expanders | `/io_expanders/list.json` | `num_gpios`, `interface`, `has_interrupt` |
| WiFi Modules | `/wifi_modules/list.json` | `core_processor`, `antenna_type`, `interface` |
| Headers | `/headers/list.json` | `pitch`, `num_pins`, `is_right_angle`, `gender` |
| FPC Connectors | `/fpc_connectors/list.json` | `pitch`, `contact_type` |
| JST Connectors | `/jst_connectors/list.json` | `pitch`, `series` |
| USB-C | `/usb_c_connectors/list.json` | `gender` |
| Switches | `/switches/list.json` | `switch_type`, `circuit`, `pin_count` |
| Fuses | `/fuses/list.json` | `current_rating`, `voltage_rating`, `response_time` |
| Accelerometers | `/accelerometers/list.json` | `interface` |
| Gyroscopes | `/gyroscopes/list.json` | `interface` |
| Potentiometers | `/potentiometers/list.json` | `maxResistance`, `pinVariant` |
| Relays | `/relays/list.json` | `relay_type` |

All endpoints also accept `package` and `limit` (max 100).

## Datasheet Download

### Step 1: Use lcsc.py (handles LCSC/szlcsc/wmsc CDN automatically)

```bash
python3 "$LCSC" datasheet C506187 -o ./datasheets
```

The script tries these LCSC sources in order:
1. szlcsc.com pdfUrl (atta.szlcsc.com CDN)
2. szlcsc item page embedded PDF links
3. wmsc.lcsc.com CDN (extracted from LCSC datasheet viewer page)

All downloads are validated with PDF magic bytes (`%PDF-` header check).

### Step 2: If script outputs `[FALLBACK]`, use curl from alternative sources

When auto-download fails, the script prints `[FALLBACK]` lines with URLs.
The agent should then try downloading from those URLs using curl/WebFetch:

```bash
# wmsc CDN (if you found the slug from the LCSC product page):
curl -sL -o datasheet.pdf 'https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/<SLUG>.pdf'

# alldatasheet.com — fetch search page, extract PDF link, then curl:
curl -sL 'https://www.alldatasheet.com/view.jsp?Searchword=AW36514' | grep -oP 'href="(https?://[^"]*\.pdf)"'

# datasheet4u.com:
curl -sL 'https://www.datasheet4u.com/share_search.php?sWord=AW36514' | grep -oP 'href="(https?://[^"]*\.pdf[^"]*)"'
```

After downloading, always verify with `file <path>` to confirm it's a real PDF.

## Response Format

When presenting search results to the user, format as a clean table:

```
| LCSC     | MPN              | Package | Stock   | Price  | Type  |
|----------|------------------|---------|---------|--------|-------|
| C139621  | BQ27421YZFR-G1A  | DSBGA-9 | 354     | $0.89  | Ext   |
```

Include the LCSC product page link for parts the user shows interest in.

## Skill Chaining

After downloading a datasheet PDF, use the `datasheet` skill to convert it to Markdown and query technical content:

```bash
python agents/skills/datasheet/scripts/datasheet.py <downloaded_pdf>
```

When the user asks about a chip on a specific board, use `netlist-query` skill first to identify the part number, then come back here to search and download.
