#!/usr/bin/env python3
"""
Allegro PST Netlist Parser → JSON
==================================
Parse Cadence Allegro / OrCAD exported pstxprt.dat, pstxnet.dat, pstchip.dat
netlist files into structured JSON for AI-powered component and net queries.

Usage:
    python3 parse_netlist.py <allegro_dir> [--name <design_name>] [--version <version>]

Output directory: ~/.cache/skills/netlist-query/<design_name>/

allegro_dir: Directory containing pstchip.dat / pstxprt.dat / pstxnet.dat
design_name: Defaults to directory name
version:     Defaults to POST_TIME from pstxprt.dat, or current date
"""

import re
import json
import shutil
import sys
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path.home() / ".cache" / "skills" / "netlist-query"

PST_SOURCE_FILES = ["pstchip.dat", "pstxprt.dat", "pstxnet.dat", "netlist.log"]


def parse_pstchip(filepath: str) -> dict:
    """Parse pstchip.dat — component library definitions (pin names, footprints, values)"""
    primitives = {}
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    blocks = re.split(r"(?=^primitive\s+')", text, flags=re.MULTILINE)
    for block in blocks:
        m = re.match(r"primitive\s+'([^']+)'", block)
        if not m:
            continue
        prim_name = m.group(1)

        pins = {}
        pin_section = re.search(r"pin\s*\n(.*?)end_pin", block, re.DOTALL)
        if pin_section:
            for pm in re.finditer(
                r"'([^']+)':\s*\n\s*PIN_NUMBER='([^']*)';\s*\n\s*PINUSE='([^']*)'",
                pin_section.group(1),
            ):
                pins[pm.group(1)] = {
                    "number": pm.group(2).strip("()"),
                    "use": pm.group(3),
                }

        body = {}
        body_section = re.search(r"body\s*\n(.*?)end_body", block, re.DOTALL)
        if body_section:
            for bm in re.finditer(r"(\w+)='([^']*)'", body_section.group(1)):
                body[bm.group(1)] = bm.group(2)

        primitives[prim_name] = {
            "part_name": body.get("PART_NAME", ""),
            "jedec_type": body.get("JEDEC_TYPE", ""),
            "value": body.get("VALUE", ""),
            "pins": pins,
        }
    return primitives


def parse_pstxprt(filepath: str) -> tuple:
    """Parse pstxprt.dat — component instance list (RefDes → component type)

    Returns: (components_dict, design_name, post_time)
    """
    components = {}
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    # Extract design name from ROOT_DRAWING
    design_name = ""
    dm = re.search(r"ROOT_DRAWING='([^']+)'", text)
    if dm:
        design_name = dm.group(1)

    # Extract POST_TIME for version tracking
    post_time = ""
    pt = re.search(r"POST_TIME='([^']+)'", text)
    if pt:
        post_time = pt.group(1).strip()

    # Extract PSTWRITER version/date from header comment
    pstwriter_info = ""
    pw = re.search(r"Using PSTWRITER\s+([^\}]+)", text)
    if pw:
        pstwriter_info = pw.group(1).strip()

    blocks = re.split(r"(?=^PART_NAME\n)", text, flags=re.MULTILINE)
    for block in blocks:
        m = re.match(r"PART_NAME\n\s+(\S+)\s+'([^']+)'", block)
        if not m:
            continue
        refdes = m.group(1)
        primitive = m.group(2)
        sch_page = ""
        pm = re.search(r"P_PATH='[^:]+:(\w+)_ins", block)
        if pm:
            sch_page = pm.group(1)
        components[refdes] = {"primitive": primitive, "schematic_page": sch_page}

    return components, design_name, post_time, pstwriter_info


def parse_pstxnet(filepath: str) -> dict:
    """Parse pstxnet.dat — net connections (Net → pin list)"""
    nets = {}
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    blocks = re.split(r"(?=^NET_NAME\n)", text, flags=re.MULTILINE)
    for block in blocks:
        m = re.match(r"NET_NAME\n'([^']+)'", block)
        if not m:
            continue
        net_name = m.group(1)
        nodes = []
        for nm in re.finditer(
            r"NODE_NAME\t(\S+)\s+(\S+)\s*\n\s+'[^']*':\s*\n\s+'([^']*)':", block
        ):
            nodes.append(
                {
                    "refdes": nm.group(1),
                    "pin_number": nm.group(2),
                    "pin_name": nm.group(3),
                }
            )
        if nodes:
            nets[net_name] = nodes
    return nets


def classify_component(refdes: str, primitive: str = "", value: str = "") -> str:
    """Classify component by RefDes prefix"""
    prefix = re.match(r"^([A-Z]+)", refdes)
    if not prefix:
        return "other"
    p = prefix.group(1)
    categories = {
        "R": "resistor",
        "C": "capacitor",
        "L": "inductor",
        "D": "diode",
        "Q": "transistor",
        "U": "ic",
        "J": "connector",
        "CON": "connector",
        "TP": "testpoint",
        "F": "fuse",
        "FB": "ferrite_bead",
        "Y": "crystal",
        "SW": "switch",
        "LED": "led",
    }
    for key in sorted(categories, key=len, reverse=True):
        if p.startswith(key):
            return categories[key]
    return "other"


def build_json(
    allegro_dir: str, design_name_override: str = None, version_override: str = None
) -> dict:
    """Build the complete JSON data structure"""
    chip_file = os.path.join(allegro_dir, "pstchip.dat")
    xprt_file = os.path.join(allegro_dir, "pstxprt.dat")
    xnet_file = os.path.join(allegro_dir, "pstxnet.dat")

    for f in [chip_file, xprt_file, xnet_file]:
        if not os.path.exists(f):
            print(f"ERROR: {f} not found", file=sys.stderr)
            sys.exit(1)

    print("Parsing pstchip.dat ...")
    primitives = parse_pstchip(chip_file)
    print("Parsing pstxprt.dat ...")
    raw_components, auto_design_name, post_time, pstwriter_info = parse_pstxprt(
        xprt_file
    )
    print("Parsing pstxnet.dat ...")
    nets = parse_pstxnet(xnet_file)

    design_name = (
        design_name_override or auto_design_name or os.path.basename(allegro_dir)
    )

    # -- version info --
    now = datetime.now()
    if version_override:
        version = version_override
    elif post_time:
        # Try to parse POST_TIME as date for version
        version = post_time
    else:
        version = now.strftime("%Y%m%d")

    # -- components --
    components = {}
    for refdes, comp in raw_components.items():
        prim = primitives.get(comp["primitive"], {})
        part_name = prim.get("part_name", comp["primitive"])
        value = prim.get("value", "")
        jedec = prim.get("jedec_type", "")
        category = classify_component(refdes, part_name, value)
        components[refdes] = {
            "refdes": refdes,
            "part_name": part_name,
            "value": value,
            "footprint": jedec,
            "category": category,
            "schematic_page": comp.get("schematic_page", ""),
            "pins": {},
        }
        if prim.get("pins"):
            for pin_name, pin_info in prim["pins"].items():
                components[refdes]["pins"][pin_info["number"]] = {
                    "name": pin_name,
                    "number": pin_info["number"],
                    "use": pin_info["use"],
                }

    # -- merge net info into components --
    comp_nets = defaultdict(dict)
    for net_name, nodes in nets.items():
        for node in nodes:
            comp_nets[node["refdes"]][node["pin_number"]] = {
                "net": net_name,
                "pin_name": node["pin_name"],
            }

    for refdes, pin_map in comp_nets.items():
        if refdes not in components:
            components[refdes] = {
                "refdes": refdes,
                "part_name": "UNKNOWN",
                "value": "",
                "footprint": "",
                "category": classify_component(refdes),
                "schematic_page": "",
                "pins": {},
            }
        for pin_num, net_info in pin_map.items():
            if pin_num not in components[refdes]["pins"]:
                components[refdes]["pins"][pin_num] = {
                    "name": net_info["pin_name"],
                    "number": pin_num,
                    "use": "UNSPEC",
                }
            components[refdes]["pins"][pin_num]["net"] = net_info["net"]

    # -- category_index --
    cat_index = defaultdict(list)
    for refdes, comp in sorted(components.items()):
        cat_index[comp["category"]].append(
            {
                "refdes": refdes,
                "part_name": comp["part_name"],
                "value": comp["value"],
                "footprint": comp["footprint"],
                "schematic_page": comp.get("schematic_page", ""),
            }
        )

    category_summary = {}
    for cat, items in sorted(cat_index.items()):
        by_part = defaultdict(list)
        for item in items:
            by_part[item["part_name"]].append(item["refdes"])
        parts_list = []
        for part_name, refdes_list in sorted(by_part.items()):
            sample = next(i for i in items if i["part_name"] == part_name)
            parts_list.append(
                {
                    "part_name": part_name,
                    "value": sample["value"],
                    "footprint": sample["footprint"],
                    "count": len(refdes_list),
                    "refdes_list": sorted(
                        refdes_list,
                        key=lambda r: (
                            re.match(r"^[A-Z]+", r).group()
                            if re.match(r"^[A-Z]+", r)
                            else "",
                            int(re.search(r"\d+", r).group())
                            if re.search(r"\d+", r)
                            else 0,
                        ),
                    ),
                }
            )
        category_summary[cat] = {
            "total": len(items),
            "unique_parts": len(by_part),
            "parts": sorted(parts_list, key=lambda p: p["part_name"]),
        }

    # -- stats --
    ic_count = sum(1 for c in components.values() if c["category"] == "ic")
    conn_count = sum(1 for c in components.values() if c["category"] == "connector")
    passive_count = sum(
        1
        for c in components.values()
        if c["category"] in ("resistor", "capacitor", "inductor")
    )

    return {
        "_meta": {
            "description": "Allegro PST netlist → JSON (AI-queryable)",
            "version": version,
            "parsed_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "source_dir": os.path.abspath(allegro_dir),
            "source_files": ["pstchip.dat", "pstxprt.dat", "pstxnet.dat"],
            "design_name": design_name,
            "post_time": post_time,
            "pstwriter": pstwriter_info,
            "stats": {
                "total_components": len(components),
                "total_nets": len(nets),
                "ics": ic_count,
                "connectors": conn_count,
                "passives": passive_count,
            },
        },
        "category_index": category_summary,
        "components": components,
        "nets": nets,
    }


def backup_source_files(allegro_dir: str, out_dir: Path):
    """Back up raw PST netlist files to the output directory"""
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for fname in PST_SOURCE_FILES:
        src = os.path.join(allegro_dir, fname)
        if os.path.isfile(src):
            dst = raw_dir / fname
            shutil.copy2(src, dst)
            copied.append(fname)

    # Also copy any extra .dat/.txt files that might be relevant
    for f in Path(allegro_dir).iterdir():
        if f.suffix in (".dat", ".txt", ".log") and f.name not in PST_SOURCE_FILES:
            dst = raw_dir / f.name
            if not dst.exists():
                shutil.copy2(f, dst)
                copied.append(f.name)

    return copied


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Allegro PST Netlist → JSON")
    parser.add_argument(
        "allegro_dir",
        help="Directory containing pstchip.dat / pstxprt.dat / pstxnet.dat",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Design name (default: inferred from ROOT_DRAWING or directory name)",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Version (default: inferred from POST_TIME or current date)",
    )
    args = parser.parse_args()

    allegro_dir = os.path.abspath(args.allegro_dir)
    result = build_json(allegro_dir, args.name, args.version)
    design_name = result["_meta"]["design_name"]
    version = result["_meta"]["version"]

    # Output to ~/.cache/skills/netlist-query/<design_name>/
    out_dir = BASE_DIR / design_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "netlist.json"

    print(f"Writing {out_file} ...")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Backup raw source files
    print("Backing up raw netlist files ...")
    copied = backup_source_files(allegro_dir, out_dir)

    # Create memory.md
    memory_file = out_dir / "memory.md"
    if not memory_file.is_file():
        memory_file.write_text(
            f"# {design_name} - Netlist Query Cache\n\n"
            f"> This file caches previously queried circuit connections for quick lookup.\n\n"
            "(no records yet)\n",
            encoding="utf-8",
        )

    stats = result["_meta"]["stats"]
    print(f"\n✅ Done!")
    print(f"   Design:     {design_name}")
    print(f"   Version:    {version}")
    print(f"   Parsed at:  {result['_meta']['parsed_at']}")
    print(
        f"   Components: {stats['total_components']} "
        f"({stats['ics']} ICs, {stats['connectors']} connectors, {stats['passives']} passives)"
    )
    print(f"   Nets:       {stats['total_nets']}")
    print(f"   Output:     {out_file}")
    print(
        f"   Raw backup: {out_dir / 'raw/'} ({len(copied)} files: {', '.join(copied)})"
    )
    print(f"   Memory:     {memory_file}")
    print(f"   Size:       {out_file.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
