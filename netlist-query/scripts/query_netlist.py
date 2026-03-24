#!/usr/bin/env python3
"""
Netlist Query Tool
==================
从已解析的 netlist.json 中查询器件和网络信息。

用法:
    query_netlist.py <设计名> <命令> [参数...]

命令:
    component <refdes>           查看器件信息及所有引脚连接
    net <net_name>               查看网络上所有节点
    peripheral <refdes>          查看某 IC 的完整外围电路（所有连接的器件）
    search <关键词>               在器件名/网络名中搜索关键词
    list-ic                      列出所有 IC
    list-category <category>     列出某类别所有器件
    pin-map <refdes>             引脚-网络映射表（适合导出）

示例:
    query_netlist.py dev4_allegro component U1700
    query_netlist.py dev4_allegro peripheral U1700
    query_netlist.py dev4_allegro search IMU
    query_netlist.py dev4_allegro net SPI_IMUTOAA_MISO
"""

import json
import sys
import os
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path.home() / ".cache" / "skills" / "netlist-query"


def load_netlist(design_name: str) -> dict:
    """加载 netlist.json"""
    # Try exact match first, then case-insensitive search
    design_dir = BASE_DIR / design_name
    if not design_dir.is_dir():
        # Search for matching directory
        for d in BASE_DIR.iterdir():
            if d.is_dir() and d.name.lower() == design_name.lower():
                design_dir = d
                break
        else:
            print(f"错误: 找不到设计 '{design_name}'", file=sys.stderr)
            print(f"已有设计:", file=sys.stderr)
            if BASE_DIR.is_dir():
                for d in sorted(BASE_DIR.iterdir()):
                    if d.is_dir():
                        print(f"  - {d.name}", file=sys.stderr)
            sys.exit(1)

    nl_file = design_dir / "netlist.json"
    if not nl_file.is_file():
        print(f"错误: {nl_file} 不存在，请先运行 parse_netlist.py", file=sys.stderr)
        sys.exit(1)

    with open(nl_file, encoding='utf-8') as f:
        return json.load(f)


def cmd_component(nl, refdes):
    """查看器件信息"""
    refdes = refdes.upper()
    comp = nl["components"].get(refdes)
    if not comp:
        print(f"未找到器件 {refdes}")
        return

    print(f"{'='*50}")
    print(f"RefDes:    {comp['refdes']}")
    print(f"Part:      {comp['part_name']}")
    print(f"Value:     {comp['value']}")
    print(f"Footprint: {comp['footprint']}")
    print(f"Category:  {comp['category']}")
    print(f"Sch Page:  {comp['schematic_page']}")
    print(f"{'='*50}")
    print(f"{'Pin':>5} {'Name':<16} {'Net':<30}")
    print(f"{'-'*5} {'-'*16} {'-'*30}")

    pins = comp.get("pins", {})
    for pin_num in sorted(pins.keys(), key=lambda x: (int(x) if x.isdigit() else 999, x)):
        pin = pins[pin_num]
        net = pin.get("net", "N/C")
        print(f"{pin_num:>5} {pin['name']:<16} {net:<30}")


def cmd_net(nl, net_name):
    """查看网络上所有节点"""
    # Case-insensitive search
    actual_name = None
    for n in nl["nets"]:
        if n.lower() == net_name.lower():
            actual_name = n
            break
    if not actual_name:
        # Partial match
        matches = [n for n in nl["nets"] if net_name.lower() in n.lower()]
        if not matches:
            print(f"未找到网络 '{net_name}'")
            return
        if len(matches) == 1:
            actual_name = matches[0]
        else:
            print(f"找到 {len(matches)} 个匹配网络:")
            for m in sorted(matches):
                print(f"  {m}")
            return

    nodes = nl["nets"][actual_name]
    print(f"Net: {actual_name}  ({len(nodes)} nodes)")
    print(f"{'-'*60}")
    for node in nodes:
        comp = nl["components"].get(node["refdes"], {})
        part = comp.get("part_name", "?")
        cat = comp.get("category", "?")
        print(f"  {node['refdes']:<10} pin {node['pin_number']:<5} ({node['pin_name']:<16}) [{part}] ({cat})")


def cmd_peripheral(nl, refdes):
    """查看某 IC 的完整外围电路（自动过滤 GND/电源噪声）"""
    refdes = refdes.upper()
    comp = nl["components"].get(refdes)
    if not comp:
        print(f"未找到器件 {refdes}")
        return

    print(f"{'='*70}")
    print(f"外围电路: {refdes} ({comp['part_name']})")
    print(f"{'='*70}")

    # Identify power/ground nets to filter (nets with many connections are usually power)
    POWER_NET_KEYWORDS = {"GND", "VCC", "VDD", "VSS", "VBUS", "VBAT", "VREG", "VPH", "NC"}
    power_nets = set()
    power_info = defaultdict(list)  # net_name -> [pin descriptions]
    for pin_num, pin in comp.get("pins", {}).items():
        net = pin.get("net")
        if not net:
            continue
        net_upper = net.upper()
        is_power = any(kw in net_upper for kw in POWER_NET_KEYWORDS)
        if not is_power:
            # Also treat nets with >20 nodes as power/ground/bus
            node_count = len(nl["nets"].get(net, []))
            if node_count > 20:
                is_power = True
        if is_power:
            power_nets.add(net)
            power_info[net].append(f"{pin_num} ({pin['name']})")

    # Show power summary first (group pins by net)
    if power_info:
        print(f"\n--- 电源/地 (已折叠) ---")
        for net in sorted(power_info.keys()):
            pin_list = power_info[net]
            if len(pin_list) > 4:
                pins_str = ", ".join(pin_list[:3]) + f" ... +{len(pin_list)-3}"
            else:
                pins_str = ", ".join(pin_list)
            node_count = len(nl["nets"].get(net, []))
            print(f"  {pins_str:<40} → {net} ({node_count} nodes)")

    # Collect signal connections (excluding power nets)
    connected = defaultdict(list)  # peer_refdes -> [(my_pin, net, peer_pin)]

    for pin_num, pin in comp.get("pins", {}).items():
        net = pin.get("net")
        if not net or net in power_nets:
            continue
        nodes = nl["nets"].get(net, [])
        for node in nodes:
            if node["refdes"] != refdes:
                connected[node["refdes"]].append({
                    "my_pin": f"{pin_num} ({pin['name']})",
                    "net": net,
                    "peer_pin": f"{node['pin_number']} ({node['pin_name']})",
                })

    # Group by category
    by_cat = defaultdict(list)
    for peer_refdes, connections in sorted(connected.items()):
        peer = nl["components"].get(peer_refdes, {})
        cat = peer.get("category", "other")
        by_cat[cat].append((peer_refdes, peer, connections))

    for cat in ["ic", "connector", "resistor", "capacitor", "inductor",
                "transistor", "diode", "testpoint", "other"]:
        items = by_cat.get(cat, [])
        if not items:
            continue
        print(f"\n--- {cat.upper()} ({len(items)}) ---")
        for peer_refdes, peer, connections in items:
            part = peer.get("part_name", "?")
            val = peer.get("value", "")
            label = f"{peer_refdes} [{part}]"
            if val and val != part:
                label += f" ({val})"
            print(f"\n  {label}")
            for c in connections:
                print(f"    {refdes}.{c['my_pin']} --[{c['net']}]--> "
                      f"{peer_refdes}.{c['peer_pin']}")


def cmd_search(nl, keyword):
    """搜索器件名和网络名"""
    kw = keyword.lower()

    # Search components
    comp_matches = []
    for refdes, comp in nl["components"].items():
        if (kw in refdes.lower() or kw in comp.get("part_name", "").lower()
                or kw in comp.get("value", "").lower()):
            comp_matches.append(comp)

    if comp_matches:
        print(f"=== 器件匹配 ({len(comp_matches)}) ===")
        for c in sorted(comp_matches, key=lambda x: x["refdes"]):
            print(f"  {c['refdes']:<12} {c['part_name']:<35} {c['value']:<15} ({c['category']})")

    # Search nets
    net_matches = [n for n in nl["nets"] if kw in n.lower()]
    if net_matches:
        print(f"\n=== 网络匹配 ({len(net_matches)}) ===")
        for n in sorted(net_matches):
            nodes = nl["nets"][n]
            node_str = ", ".join(f"{nd['refdes']}.{nd['pin_name']}" for nd in nodes[:5])
            if len(nodes) > 5:
                node_str += f" ... +{len(nodes)-5}"
            print(f"  {n:<35} → {node_str}")

    if not comp_matches and not net_matches:
        print(f"未找到匹配 '{keyword}' 的器件或网络")


def cmd_list_ic(nl):
    """列出所有 IC"""
    ci = nl.get("category_index", {}).get("ic", {})
    if not ci:
        print("未找到 IC 分类信息")
        return

    print(f"=== IC 列表 ({ci['total']} 个器件, {ci['unique_parts']} 种型号) ===\n")
    print(f"{'型号':<40} {'值':<25} {'数量':>4}  {'标号'}")
    print(f"{'-'*40} {'-'*25} {'-'*4}  {'-'*30}")
    for p in ci["parts"]:
        refs = ", ".join(p["refdes_list"][:6])
        if len(p["refdes_list"]) > 6:
            refs += f" +{len(p['refdes_list'])-6}"
        val = p["value"] if p["value"] != p["part_name"] else ""
        print(f"{p['part_name']:<40} {val:<25} {p['count']:>4}  {refs}")


def cmd_list_category(nl, category):
    """列出某类别所有器件"""
    ci = nl.get("category_index", {}).get(category.lower(), {})
    if not ci:
        avail = ", ".join(sorted(nl.get("category_index", {}).keys()))
        print(f"未找到类别 '{category}'。可用类别: {avail}")
        return

    print(f"=== {category.upper()} ({ci['total']} 个, {ci['unique_parts']} 种型号) ===\n")
    for p in ci["parts"]:
        refs = ", ".join(p["refdes_list"][:8])
        if len(p["refdes_list"]) > 8:
            refs += f" +{len(p['refdes_list'])-8}"
        val = f" [{p['value']}]" if p["value"] else ""
        print(f"  {p['part_name']}{val}  ×{p['count']}  ({refs})")


def cmd_pin_map(nl, refdes):
    """引脚-网络映射表"""
    refdes = refdes.upper()
    comp = nl["components"].get(refdes)
    if not comp:
        print(f"未找到器件 {refdes}")
        return

    print(f"# {refdes} ({comp['part_name']}) Pin Map\n")
    print(f"| Pin | Name | Net | Connected To |")
    print(f"|-----|------|-----|-------------|")

    for pin_num in sorted(comp.get("pins", {}).keys(),
                          key=lambda x: (int(x) if x.isdigit() else 999, x)):
        pin = comp["pins"][pin_num]
        net = pin.get("net", "")
        peers = ""
        if net:
            nodes = nl["nets"].get(net, [])
            peer_list = [f"{n['refdes']}.{n['pin_name']}"
                         for n in nodes if n["refdes"] != refdes]
            peers = ", ".join(peer_list[:4])
            if len(peer_list) > 4:
                peers += f" +{len(peer_list)-4}"
        print(f"| {pin_num} | {pin['name']} | {net} | {peers} |")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        # List available designs
        if BASE_DIR.is_dir():
            print("\n已解析的设计:")
            for d in sorted(BASE_DIR.iterdir()):
                if d.is_dir() and (d / "netlist.json").is_file():
                    print(f"  - {d.name}")
        sys.exit(1)

    design_name = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:]

    nl = load_netlist(design_name)

    commands = {
        "component": (cmd_component, 1, "<refdes>"),
        "net": (cmd_net, 1, "<net_name>"),
        "peripheral": (cmd_peripheral, 1, "<refdes>"),
        "search": (cmd_search, 1, "<关键词>"),
        "list-ic": (cmd_list_ic, 0, ""),
        "list-category": (cmd_list_category, 1, "<category>"),
        "pin-map": (cmd_pin_map, 1, "<refdes>"),
    }

    if command not in commands:
        print(f"未知命令: {command}")
        print(f"可用命令: {', '.join(commands.keys())}")
        sys.exit(1)

    func, nargs, usage = commands[command]
    if len(args) < nargs:
        print(f"用法: query_netlist.py <设计名> {command} {usage}")
        sys.exit(1)

    if nargs == 0:
        func(nl)
    else:
        func(nl, *args[:nargs])


if __name__ == "__main__":
    main()
