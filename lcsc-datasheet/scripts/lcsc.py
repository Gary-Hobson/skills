#!/usr/bin/env python3
"""
LCSC (立创商城) Component Search & Datasheet Download Tool

Powered by JLCSearch API (https://jlcsearch.tscircuit.com)

Usage:
    python3 lcsc.py search <keyword>              # Search by MPN / keyword
    python3 lcsc.py resistor 10k 0603             # Search resistor by value & package
    python3 lcsc.py capacitor 100nF 0603          # Search capacitor by value & package
    python3 lcsc.py ldo 3.3 SOT-23                # Search LDO by output voltage
    python3 lcsc.py mcu --core ARM --flash 64     # Search MCU by specs
    python3 lcsc.py mosfet --vds 30 --package SOT-23
    python3 lcsc.py info C139621                   # Show part details
    python3 lcsc.py datasheet C139621              # Download datasheet PDF
"""

import argparse
import json
import os
import re
import subprocess
import sys
from urllib.parse import quote, urlencode

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

JLCSEARCH_BASE = "https://jlcsearch.tscircuit.com"
LCSC_DATASHEET = "https://www.lcsc.com/datasheet/{lcsc}.pdf"
LCSC_PRODUCT = "https://www.lcsc.com/product-detail/{lcsc}.html"
SZLCSC_SEARCH = "https://so.szlcsc.com/global.html"
SZLCSC_ITEM = "https://item.szlcsc.com/{item_id}.html"

# ── HTTP client (requests or curl fallback) ─────────────────────────
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

if HAS_REQUESTS:
    session = requests.Session()
    session.headers["User-Agent"] = UA
    _retry = Retry(
        total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
    )
    session.mount("https://", HTTPAdapter(max_retries=_retry))

    def http_get(
        url: str, params: dict | None = None, timeout: int = 15, stream: bool = False
    ):
        return session.get(url, params=params, timeout=timeout, stream=stream)
else:
    # curl-based fallback for environments without requests
    class _CurlResponse:
        def __init__(self, body: bytes, status: int, headers: dict):
            self.content = body
            self.text = body.decode("utf-8", errors="replace")
            self.status_code = status
            self.headers = headers

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")

        def json(self):
            return json.loads(self.text)

        def iter_content(self, chunk_size=8192):
            yield self.content

    def http_get(
        url: str, params: dict | None = None, timeout: int = 15, stream: bool = False
    ):
        if params:
            params = {k: v for k, v in params.items() if v is not None}
            url = url + "?" + urlencode(params)
        cmd = [
            "curl",
            "-sL",
            "-H",
            f"User-Agent: {UA}",
            "--max-time",
            str(timeout),
            url,
        ]
        if stream:
            cmd.extend(["-D", "/dev/stderr"])
        result = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
        headers = {}
        for line in result.stderr.decode(errors="replace").splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                headers[k.strip().lower()] = v.strip()
        return _CurlResponse(
            result.stdout, 200 if result.returncode == 0 else 500, headers
        )

    session = None  # not used in curl mode


# ── value parsing ───────────────────────────────────────────────────
def parse_resistance(value: str) -> float | None:
    """Parse resistance string to ohms.  e.g. '10k' -> 10000"""
    m = re.match(r"^([\d.]+)\s*([kKmMrR]?)(?:[oO]hm)?$", value.strip())
    if not m:
        return None
    num = float(m.group(1))
    suffix = m.group(2).upper()
    return num * {"K": 1e3, "M": 1e6, "R": 1, "": 1}.get(suffix, 1)


def parse_capacitance(value: str) -> float | None:
    """Parse capacitance string to farads.  e.g. '100nF' -> 1e-7"""
    m = re.match(r"^([\d.]+)\s*([pPnNuUmM])?[fF]?$", value.strip())
    if not m:
        return None
    num = float(m.group(1))
    suffix = (m.group(2) or "").upper()
    return num * {"P": 1e-12, "N": 1e-9, "U": 1e-6, "M": 1e-3, "": 1}.get(suffix, 1)


# ── JLCSearch API ───────────────────────────────────────────────────
def jlcsearch_search(query: str, limit: int = 20, **filters) -> list[dict]:
    """Search components via /api/search (supports MPN, LCSC number, description)."""
    params = {"q": query, "limit": min(limit, 100)}
    params.update({k: v for k, v in filters.items() if v is not None})
    try:
        resp = http_get(f"{JLCSEARCH_BASE}/api/search", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("components", [])
    except Exception as e:
        print(f"[warn] JLCSearch /api/search failed: {e}", file=sys.stderr)
        return []


def jlcsearch_list(endpoint: str, params: dict, limit: int = 20) -> list[dict]:
    """Call a typed JLCSearch endpoint (e.g. /resistors/list.json)."""
    params["limit"] = min(limit, 100)
    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}
    try:
        resp = http_get(
            f"{JLCSEARCH_BASE}/{endpoint}/list.json", params=params, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        for v in data.values():
            if isinstance(v, list):
                return v
        return []
    except Exception as e:
        print(f"[warn] JLCSearch /{endpoint} failed: {e}", file=sys.stderr)
        return []


# ── szlcsc.com fallback (for part details) ──────────────────────────
def _szlcsc_get_detail(lcsc: str) -> dict | None:
    """Get part details from szlcsc.com item page (HTML scraping)."""
    try:
        resp = http_get(SZLCSC_SEARCH, params={"k": lcsc}, timeout=15)
        resp.raise_for_status()
        item_match = re.search(r"item\.szlcsc\.com/(\d+)\.html", resp.text)
        if not item_match:
            return None

        item_resp = http_get(
            SZLCSC_ITEM.format(item_id=item_match.group(1)), timeout=15
        )
        item_resp.raise_for_status()
        html = item_resp.text

        def extract(pattern, default=""):
            m = re.search(pattern, html)
            return m.group(1).strip() if m else default

        product_code = extract(r'"productCode":"(C\d+)"') or lcsc
        prices = []
        for pm in re.finditer(r'"ladder":(\d+).*?"productPrice":"?([\d.]+)"?', html):
            prices.append({"qty": int(pm.group(1)), "price": pm.group(2)})

        return {
            "lcsc": product_code,
            "mfr": extract(r'"productModel":"([^"]+)"'),
            "manufacturer": extract(r'"brandNameEn":"([^"]+)"')
            or extract(r'"brandName":"([^"]+)"'),
            "package": extract(r'"encapStandard":"([^"]+)"'),
            "description": extract(r'"productIntroEn":"([^"]+)"')
            or extract(r'"productIntro":"([^"]+)"'),
            "category": extract(r'"parentCatalogName":"([^"]+)"'),
            "stock": extract(r'"stockNumber":(\d+)'),
            "datasheet": extract(r'"pdfUrl":"([^"]+)"')
            or LCSC_DATASHEET.format(lcsc=product_code),
            "product_page": LCSC_PRODUCT.format(lcsc=product_code),
            "prices": prices,
        }
    except Exception:
        return None


def get_part_info(lcsc: str) -> dict:
    """Get part info: JLCSearch API first, szlcsc.com for details."""
    if not lcsc.startswith("C"):
        lcsc = f"C{lcsc}"

    # JLCSearch for basic info
    lcsc_num = lcsc.lstrip("C")
    results = jlcsearch_search(lcsc_num, limit=1)
    jlc_info = results[0] if results else {}

    # szlcsc for richer details (description, prices, datasheet URL)
    szlcsc_info = _szlcsc_get_detail(lcsc) or {}

    # Merge: prefer szlcsc for detail fields, JLCSearch for stock/price
    return {
        "lcsc": lcsc,
        "mfr": szlcsc_info.get("mfr") or jlc_info.get("mfr", ""),
        "manufacturer": szlcsc_info.get("manufacturer") or "",
        "package": szlcsc_info.get("package") or jlc_info.get("package", ""),
        "description": szlcsc_info.get("description")
        or jlc_info.get("description", ""),
        "category": szlcsc_info.get("category", ""),
        "stock": szlcsc_info.get("stock") or jlc_info.get("stock", ""),
        "datasheet": szlcsc_info.get("datasheet") or LCSC_DATASHEET.format(lcsc=lcsc),
        "product_page": szlcsc_info.get("product_page")
        or LCSC_PRODUCT.format(lcsc=lcsc),
        "prices": szlcsc_info.get("prices", []),
    }


# ── Datasheet download ─────────────────────────────────────────────

WMSC_CDN = "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/{filename}"


def _is_valid_pdf(filepath: str) -> bool:
    """Check file starts with %PDF magic bytes."""
    try:
        with open(filepath, "rb") as f:
            header = f.read(8)
        return header[:5] == b"%PDF-"
    except Exception:
        return False


def _download_pdf(url: str, filepath: str) -> bool:
    """Download a URL to filepath; validate it's a real PDF (>1KB, %PDF header)."""
    try:
        if HAS_REQUESTS:
            resp = requests.get(
                url, headers={"User-Agent": UA}, timeout=(15, 120), stream=True
            )
        else:
            resp = http_get(url, timeout=120, stream=True)
        resp.raise_for_status()

        ct = resp.headers.get("Content-Type", "")
        if "html" in ct and "pdf" not in ct:
            return False

        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(
                        f"\r  {downloaded // 1024} KB / {total // 1024} KB ({pct}%)",
                        end="",
                        flush=True,
                    )
        if total:
            print()

        # Validate: must be >1KB and start with %PDF
        size = os.path.getsize(filepath)
        if size < 1024 or not _is_valid_pdf(filepath):
            os.remove(filepath)
            return False

        print(f"  Saved: {filepath} ({size // 1024} KB)")
        return True
    except Exception:
        if os.path.exists(filepath):
            os.remove(filepath)
        return False


def _scrape_datasheet_urls(lcsc: str) -> list[tuple[str, str]]:
    """Scrape szlcsc.com for datasheet PDF URLs.

    Returns list of (source_label, url) tuples.
    Covers: atta.szlcsc.com direct links, wmsc CDN filename extraction.
    """
    urls: list[tuple[str, str]] = []
    seen: set[str] = set()

    try:
        search_resp = http_get(SZLCSC_SEARCH, params={"k": lcsc}, timeout=10)
        item_match = re.search(r"item\.szlcsc\.com/(\d+)\.html", search_resp.text)
        if not item_match:
            return urls

        item_resp = http_get(
            SZLCSC_ITEM.format(item_id=item_match.group(1)), timeout=10
        )
        html = item_resp.text

        # 1. pdfUrl field from embedded JSON (atta.szlcsc.com)
        pdf_match = re.search(r'"pdfUrl":"(https?://[^"]+\.pdf[^"]*)"', html)
        if pdf_match:
            u = pdf_match.group(1)
            urls.append(("szlcsc-pdfUrl", u))
            seen.add(u)

        # 2. All other PDF links in page
        for m in re.finditer(r'"(https?://[^"]+\.pdf[^"]*)"', html):
            u = m.group(1)
            if u not in seen and "iso" not in u.lower() and "static.szlcsc" not in u:
                urls.append(("szlcsc", u))
                seen.add(u)

        # 3. Extract wmsc CDN filename from the LCSC datasheet page slug.
        #    LCSC datasheet pages use a slug like:
        #      lcsc_datasheet_{date}_{Mfr}_{MPN}_{LCSC}.pdf
        #    The actual CDN URL is:
        #      wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/{slug}.pdf
        #    We look for that slug in szlcsc page data.
        for m in re.finditer(
            r"(lcsc_datasheet_\d+_[A-Za-z0-9_\-]+_" + re.escape(lcsc) + r"\.pdf)",
            html,
        ):
            slug = m.group(1)
            cdn_url = WMSC_CDN.format(filename=slug)
            if cdn_url not in seen:
                urls.append(("wmsc-cdn", cdn_url))
                seen.add(cdn_url)

    except Exception:
        pass

    return urls


def _scrape_lcsc_datasheet_slug(lcsc: str) -> str | None:
    """Fetch the LCSC datasheet viewer page and extract the wmsc CDN slug.

    The page at https://www.lcsc.com/datasheet/{lcsc}.pdf is a JS viewer,
    but the HTML often embeds the real CDN path in script tags or meta.
    """
    try:
        resp = http_get(f"https://www.lcsc.com/datasheet/{lcsc}.pdf", timeout=10)
        for m in re.finditer(
            r"(lcsc_datasheet_\d+_[A-Za-z0-9_\-]+_" + re.escape(lcsc) + r"\.pdf)",
            resp.text,
        ):
            return m.group(1)
        for m in re.finditer(
            r'wmsc\.lcsc\.com/wmsc/upload/file/pdf/v2/lcsc/([^"\'\\s]+\.pdf)',
            resp.text,
        ):
            return m.group(1)
    except Exception:
        pass
    return None


# MPN prefix → (tag, URL template)
# {mpn} = full base MPN, {lower} = lowercase base MPN
_MFR_URL_TEMPLATES = [
    (
        r"(?i)^(MAX|AD[0-9]|ADP|ADM|LTC|LT[0-9]|HMC|ADUM|SSM|ADAU)",
        "adi",
        "https://www.analog.com/media/en/technical-documentation/data-sheets/{lower}.pdf",
    ),
    (
        r"(?i)^(BQ|TPS|LM[0-9]|OPA|ADS1|MSP|TMS|CC[0-9]{4}|DRV|INA|TLV|REF[0-9]|SN[0-9])",
        "ti",
        "https://www.ti.com/lit/ds/symlink/{lower}.pdf",
    ),
    (
        r"(?i)^(STM|LSM|LIS|LPS|VL[0-9]|L6[0-9]|LD[0-9]|ST[BL])",
        "st",
        "https://www.st.com/resource/en/datasheet/{lower}.pdf",
    ),
    (
        r"(?i)^(NRF|NPM)",
        "nordic",
        "https://docs.nordicsemi.com/bundle/{lower}/page/{mpn}_PS_latest.pdf",
    ),
]


def _guess_mfr_direct_urls(mpn_base: str) -> list[tuple[str, str]]:
    lower = mpn_base.lower()
    urls = []
    for pattern, tag, template in _MFR_URL_TEMPLATES:
        if re.match(pattern, mpn_base):
            url = template.format(mpn=mpn_base, lower=lower)
            urls.append((tag, url))
    return urls


def download_datasheet(lcsc: str, output_dir: str = ".") -> str | None:
    if not lcsc.startswith("C"):
        lcsc = f"C{lcsc}"

    info = get_part_info(lcsc)
    mfr = info.get("mfr") or lcsc

    if info.get("mfr"):
        print(f"Part: {mfr} ({info.get('manufacturer', '')})")
        print(f"LCSC: {info['lcsc']}")
        print()

    filename = re.sub(r"[^\w\-.]", "_", mfr) + "_datasheet.pdf"
    filepath = os.path.join(output_dir, filename)

    urls: list[tuple[str, str]] = []
    seen: set[str] = set()

    def _add(source: str, url: str):
        if url and url not in seen:
            urls.append((source, url))
            seen.add(url)

    info_ds = info.get("datasheet", "")
    if info_ds and ("atta.szlcsc.com" in info_ds or "wmsc.lcsc.com" in info_ds):
        _add("szlcsc-info", info_ds)

    for source, url in _scrape_datasheet_urls(lcsc):
        _add(source, url)

    slug = _scrape_lcsc_datasheet_slug(lcsc)
    if slug:
        _add("wmsc-cdn", WMSC_CDN.format(filename=slug))

    for source, url in urls:
        print(f"  [{source}] {url}")
        if _download_pdf(url, filepath):
            return filepath

    mpn_base = re.split(r"[-+]", mfr)[0]

    mfr_direct_urls = _guess_mfr_direct_urls(mpn_base)

    for tag, url in mfr_direct_urls:
        print(f"  [{tag}] {url}")
        if _download_pdf(url, filepath):
            return filepath

    print()
    print(f"[FALLBACK] LCSC auto-download failed for {mfr} ({lcsc}).")
    print(f"[FALLBACK] output={filepath}")
    for tag, url in mfr_direct_urls:
        print(f"[FALLBACK] curl -sL -o '{filepath}' '{url}'")
    print(f"[FALLBACK] browse: https://www.lcsc.com/product-detail/{lcsc}.html")
    print(
        f"[FALLBACK] browse: https://www.alldatasheet.com/view.jsp?Searchword={quote(mfr)}"
    )
    print(
        f"[FALLBACK] browse: https://www.datasheet4u.com/share_search.php?sWord={quote(mfr)}"
    )

    return None


# ── Display helpers ─────────────────────────────────────────────────
def fmt_lcsc(lcsc) -> str:
    if isinstance(lcsc, int):
        return f"C{lcsc}"
    s = str(lcsc)
    return s if s.startswith("C") else f"C{s}"


def print_table(parts: list[dict]):
    if not parts:
        print("No results found.")
        return
    cols = [
        ("LCSC", "lcsc", 10),
        ("MPN", "mfr", 24),
        ("Package", "package", 12),
        ("Stock", "stock", 10),
        ("Price", "price", 10),
        ("Type", "library_type", 8),
    ]
    header = " | ".join(h.ljust(w) for h, _, w in cols)
    sep = "-+-".join("-" * w for _, _, w in cols)
    print(header)
    print(sep)
    for p in parts:
        row = []
        for _, key, w in cols:
            val = p.get(key, "")
            if key == "lcsc":
                val = fmt_lcsc(val)
            elif key == "price":
                v = p.get("price") or p.get("price1") or ""
                if v:
                    try:
                        val = f"${float(v):.4f}"
                    except (ValueError, TypeError):
                        val = str(v)
                else:
                    val = ""
            elif key == "library_type":
                if "is_basic" in p:
                    val = "Basic" if p["is_basic"] else "Ext"
                elif "is_preferred" in p:
                    val = "Pref" if p["is_preferred"] else "Ext"
                else:
                    val = p.get("library_type", "")
            val = str(val)[:w]
            row.append(val.ljust(w))
        print(" | ".join(row))
    print(f"\n({len(parts)} results)")


def print_info(info: dict):
    if not info:
        print("Part not found.")
        return
    rows = [
        ("LCSC", info.get("lcsc", "")),
        ("MPN", info.get("mfr", "")),
        ("Manufacturer", info.get("manufacturer", "")),
        ("Package", info.get("package", "")),
        ("Category", info.get("category", "")),
        ("Description", info.get("description", "")),
        ("Stock", str(info.get("stock", ""))),
        ("Datasheet", info.get("datasheet", "")),
        ("Product Page", info.get("product_page", "")),
    ]
    prices = info.get("prices", [])
    if prices:
        price_str = ", ".join(
            f"{p['qty']}+: ¥{p['price']}" for p in prices if p.get("price")
        )
        rows.append(("Prices", price_str))

    max_label = max(len(r[0]) for r in rows)
    for label, val in rows:
        if val:
            print(f"  {label.rjust(max_label)} : {val}")


# ── CLI ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="LCSC Component Search & Datasheet Download (via JLCSearch API)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s search BQ27421                  Search by MPN
  %(prog)s search "LDO 3.3V SOT-23"       Search by keyword
  %(prog)s resistor 10k 0603              Search 10kΩ 0603 resistor
  %(prog)s capacitor 100nF 0603           Search 100nF 0603 capacitor
  %(prog)s ldo 3.3                         Search 3.3V LDO
  %(prog)s mcu --core ARM --flash 64       Search MCU
  %(prog)s mosfet --vds 30 --package SOT-23
  %(prog)s diode --type schottky
  %(prog)s led --color red --package 0603
  %(prog)s info C139621                    Show part details
  %(prog)s datasheet C139621               Download datasheet PDF
  %(prog)s datasheet C139621 -o ./pdf      Download to directory
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # search (generic)
    p_s = sub.add_parser("search", aliases=["s"], help="Search by keyword / MPN")
    p_s.add_argument("keyword", nargs="+", help="Search keyword(s)")
    p_s.add_argument("-n", "--limit", type=int, default=20)
    p_s.add_argument("--basic", action="store_true", help="Only basic library parts")
    p_s.add_argument("--package", help="Filter by package")

    # resistor
    p_r = sub.add_parser("resistor", aliases=["r"], help="Search resistor by value")
    p_r.add_argument("value", help="e.g. 10k, 4.7M, 100")
    p_r.add_argument("package", nargs="?", help="e.g. 0603, 0805")
    p_r.add_argument("-n", "--limit", type=int, default=20)
    p_r.add_argument("--basic", action="store_true")

    # capacitor
    p_c = sub.add_parser("capacitor", aliases=["c"], help="Search capacitor by value")
    p_c.add_argument("value", help="e.g. 100nF, 10uF, 1pF")
    p_c.add_argument("package", nargs="?", help="e.g. 0603, 0805")
    p_c.add_argument("-n", "--limit", type=int, default=20)
    p_c.add_argument("--basic", action="store_true")

    # ldo
    p_ldo = sub.add_parser("ldo", help="Search LDO by output voltage")
    p_ldo.add_argument("voltage", type=float, help="Output voltage (e.g. 3.3, 1.8)")
    p_ldo.add_argument("package", nargs="?", help="e.g. SOT-23, SOT-223")
    p_ldo.add_argument("-n", "--limit", type=int, default=20)

    # voltage regulator
    p_vreg = sub.add_parser("vreg", help="Search voltage regulator")
    p_vreg.add_argument("voltage", type=float, help="Output voltage")
    p_vreg.add_argument("--package", help="Package filter")
    p_vreg.add_argument("--ldo", action="store_true", help="LDO only")
    p_vreg.add_argument("-n", "--limit", type=int, default=20)

    # mcu
    p_mcu = sub.add_parser("mcu", help="Search microcontroller")
    p_mcu.add_argument("--core", help="e.g. ARM, RISC-V")
    p_mcu.add_argument("--flash", type=int, help="Min flash KB")
    p_mcu.add_argument("--ram", type=int, help="Min RAM KB")
    p_mcu.add_argument("--package", help="Package filter")
    p_mcu.add_argument("--interface", help="Interface filter")
    p_mcu.add_argument("-n", "--limit", type=int, default=20)

    # mosfet
    p_mos = sub.add_parser("mosfet", help="Search MOSFET")
    p_mos.add_argument("--vds", type=float, help="Min Vds (V)")
    p_mos.add_argument("--id", type=float, dest="drain_current", help="Min Id (A)")
    p_mos.add_argument("--package", help="Package filter")
    p_mos.add_argument("-n", "--limit", type=int, default=20)

    # diode
    p_dio = sub.add_parser("diode", help="Search diode")
    p_dio.add_argument("--type", dest="diode_type", help="e.g. schottky, zener, tvs")
    p_dio.add_argument("--package", help="Package filter")
    p_dio.add_argument("-n", "--limit", type=int, default=20)

    # led
    p_led = sub.add_parser("led", help="Search LED")
    p_led.add_argument("--color", help="e.g. red, green, blue, white")
    p_led.add_argument("--package", help="e.g. 0603, 0805")
    p_led.add_argument("-n", "--limit", type=int, default=20)

    # connector
    p_conn = sub.add_parser("connector", aliases=["conn"], help="Search connectors")
    p_conn.add_argument(
        "type", choices=["header", "fpc", "jst", "usbc"], help="Connector type"
    )
    p_conn.add_argument("--pitch", type=float, help="Pitch in mm")
    p_conn.add_argument("--pins", type=int, help="Number of pins")
    p_conn.add_argument("-n", "--limit", type=int, default=20)

    # info
    p_i = sub.add_parser("info", aliases=["i"], help="Part details by LCSC number")
    p_i.add_argument("lcsc", help="e.g. C139621")

    # datasheet
    p_d = sub.add_parser(
        "datasheet", aliases=["d", "ds"], help="Download datasheet PDF"
    )
    p_d.add_argument("lcsc", help="e.g. C139621")
    p_d.add_argument("-o", "--output", default=".", help="Output directory")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    cmd = args.command

    if cmd in ("search", "s"):
        keyword = " ".join(args.keyword)
        print(f"Searching: {keyword}\n")
        filters = {}
        if getattr(args, "basic", False):
            filters["is_basic"] = True
        if getattr(args, "package", None):
            filters["package"] = args.package
        results = jlcsearch_search(keyword, limit=args.limit, **filters)
        print_table(results)

    elif cmd in ("resistor", "r"):
        ohms = parse_resistance(args.value)
        if ohms is None:
            print(f"[error] Cannot parse: {args.value}", file=sys.stderr)
            sys.exit(1)
        params = {"resistance": ohms, "package": args.package}
        if args.basic:
            params["is_basic"] = True
        print(
            f"Searching resistors: {ohms}Ω"
            + (f" {args.package}" if args.package else "")
            + "\n"
        )
        print_table(jlcsearch_list("resistors", params, limit=args.limit))

    elif cmd in ("capacitor", "c"):
        farads = parse_capacitance(args.value)
        if farads is None:
            print(f"[error] Cannot parse: {args.value}", file=sys.stderr)
            sys.exit(1)
        params = {"capacitance": farads, "package": args.package}
        if args.basic:
            params["is_basic"] = True
        print(
            f"Searching capacitors: {farads}F"
            + (f" {args.package}" if args.package else "")
            + "\n"
        )
        print_table(jlcsearch_list("capacitors", params, limit=args.limit))

    elif cmd == "ldo":
        params = {"output_voltage": args.voltage, "package": args.package}
        print(
            f"Searching LDOs: {args.voltage}V"
            + (f" {args.package}" if args.package else "")
            + "\n"
        )
        print_table(jlcsearch_list("ldos", params, limit=args.limit))

    elif cmd == "vreg":
        params = {"output_voltage": args.voltage, "package": args.package}
        if args.ldo:
            params["is_ldo"] = True
        print(f"Searching voltage regulators: {args.voltage}V\n")
        print_table(jlcsearch_list("voltage_regulators", params, limit=args.limit))

    elif cmd == "mcu":
        params = {
            "core": args.core,
            "flash_min": args.flash,
            "ram_min": args.ram,
            "package": args.package,
            "interface": args.interface,
        }
        print(f"Searching MCUs...\n")
        print_table(jlcsearch_list("microcontrollers", params, limit=args.limit))

    elif cmd == "mosfet":
        params = {
            "drain_source_voltage_min": args.vds,
            "continuous_drain_current_min": args.drain_current,
            "package": args.package,
        }
        print(f"Searching MOSFETs...\n")
        print_table(jlcsearch_list("mosfets", params, limit=args.limit))

    elif cmd == "diode":
        params = {"diode_type": args.diode_type, "package": args.package}
        print(f"Searching diodes...\n")
        print_table(jlcsearch_list("diodes", params, limit=args.limit))

    elif cmd == "led":
        params = {"color": args.color, "package": args.package}
        print(f"Searching LEDs...\n")
        print_table(jlcsearch_list("leds", params, limit=args.limit))

    elif cmd in ("connector", "conn"):
        endpoint_map = {
            "header": ("headers", {"pitch": args.pitch, "num_pins": args.pins}),
            "fpc": ("fpc_connectors", {"pitch": args.pitch}),
            "jst": ("jst_connectors", {"pitch": args.pitch}),
            "usbc": ("usb_c_connectors", {}),
        }
        endpoint, params = endpoint_map[args.type]
        print(f"Searching {args.type} connectors...\n")
        print_table(jlcsearch_list(endpoint, params, limit=args.limit))

    elif cmd in ("info", "i"):
        print(f"Fetching: {args.lcsc}\n")
        print_info(get_part_info(args.lcsc))

    elif cmd in ("datasheet", "d", "ds"):
        os.makedirs(args.output, exist_ok=True)
        download_datasheet(args.lcsc, args.output)


if __name__ == "__main__":
    main()
