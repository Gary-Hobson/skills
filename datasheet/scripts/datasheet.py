#!/usr/bin/env python3
"""PDF 数据手册转换工具：PDF 转 Markdown + 书签索引生成。

用法:
  datasheet.py <pdf路径>

输出目录: ~/.cache/skills/datasheet/<文档名>/

前置条件: 需要安装 marker-pdf（pip install marker-pdf）
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path.home() / ".cache" / "skills" / "datasheet"


def main():
    if len(sys.argv) != 2 or sys.argv[1].startswith("-"):
        print(f"用法: {sys.argv[0]} <pdf路径>")
        sys.exit(1)

    pdf = Path(sys.argv[1]).resolve()
    if not pdf.is_file():
        print(f"错误: 文件不存在: {pdf}", file=sys.stderr)
        sys.exit(1)

    marker = shutil.which("marker_single")
    if not marker:
        print("错误: marker_single 未安装", file=sys.stderr)
        print("请手动安装: pip install marker-pdf", file=sys.stderr)
        print("详见: .claude/skills/datasheet/references/setup.md", file=sys.stderr)
        sys.exit(1)

    doc_name = pdf.stem
    doc_dir = BASE_DIR / doc_name

    print("=" * 42)
    print(f"输入: {pdf}")
    print(f"输出: {doc_dir}/")
    print("=" * 42)

    BASE_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [marker, str(pdf), "--output_dir", str(BASE_DIR), "--output_format", "markdown"],
        check=True,
    )

    md_file = doc_dir / f"{doc_name}.md"
    if not md_file.is_file():
        print(f"错误: 未生成 Markdown 文件: {md_file}", file=sys.stderr)
        sys.exit(1)

    # memory 文件
    memory_file = doc_dir / "memory.md"
    if not memory_file.is_file():
        memory_file.write_text(
            f"# {doc_name} - 已读内容索引\n\n"
            f"> 本文件记录从 `{md_file}` 实际读取过的内容位置，\n"
            "> 用于后续快速定位，避免重复搜索。\n\n"
            "（暂无记录）\n",
            encoding="utf-8",
        )

    # 书签索引
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

    # 摘要
    line_count = sum(1 for _ in md_file.open(encoding="utf-8"))
    size_kb = md_file.stat().st_size / 1024
    print("=" * 42)
    print(f"Markdown : {md_file}  ({size_kb:.0f}K, {line_count} 行)")
    if bm_count:
        print(f"书签索引 : {bookmarks_file}  ({bm_count} 条)")
        lines = bookmarks_file.read_text(encoding="utf-8").splitlines()
        print(f"\n前 20 条书签:\n{'-' * 40}")
        for line in lines[:20]:
            print(line)
        if len(lines) > 20:
            print(f"... (共 {len(lines)} 条)")
    print(f"Memory   : {memory_file}")


if __name__ == "__main__":
    main()
