#!/usr/bin/env python3
"""结绳 — 扫描已有论文，输出紧凑摘要供 Agent 比对（机械活）。

职责：扫 workspace/memory/papers/*.md，逐篇读出 {id, title, 核心假设, 关联} 并以 JSON 输出。
**不调用大模型、不联网、无 key。** 这只是从 markdown 现读的扫描 helper——
markdown 仍是唯一真相源，这里**不是** SQLite 索引（那是 B3，本脚本不碰）。

用途：SOP 第 4 步「主动连点」前，Agent 调它拿到已有论文的核心假设，逐一比对判断有无关系。

用法：
    python scripts/list_papers.py
    python scripts/list_papers.py --workspace /path/to/workspace
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _md import bullets, extract_title, iter_paper_files, section_body  # noqa: E402
from _paths import papers_dir, resolve_workspace  # noqa: E402


def summarize(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return {
        "id": path.stem,
        "title": extract_title(text),
        "核心假设": bullets(section_body(text, "核心假设")),
        "关联": bullets(section_body(text, "关联")),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="扫描 memory/papers/*.md，输出 {id,title,核心假设,关联} 摘要（不联网、不调大模型）"
    )
    parser.add_argument(
        "--workspace",
        help="覆盖 workspace 目录（默认 $JIESHENG_WORKSPACE 或 ~/.jiesheng/workspace）",
    )
    args = parser.parse_args(argv)

    workspace = resolve_workspace(args.workspace)
    pdir = papers_dir(workspace)
    papers = [summarize(p) for p in iter_paper_files(pdir)]

    json.dump(papers, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
