#!/usr/bin/env python3
"""结绳 — 把检索命中追加进 workspace/READING_LIST.md（机械活）。

**不调用大模型、不联网、无 key。** arXiv 检索由 QClaw 运行时自带的 web 工具完成；
本脚本只负责把用户确认后的命中**幂等**追加到待读清单，**按 arXiv id 去重**。

输入（二选一）：
  1) JSON：单个对象或对象数组，每项 {arxiv_id, title, why}
       {"arxiv_id": "2106.01234", "title": "…", "why": "命中我的非平稳卡点"}
     从 --input 文件 或 stdin 读。
  2) 单条 CLI：--arxiv-id … --title … --why …（给了 --arxiv-id 就走这条，忽略 stdin）

用法：
    python scripts/add_to_reading_list.py --input hits.json
    echo '[{"arxiv_id":"2106.01234","title":"X","why":"Y"}]' | python scripts/add_to_reading_list.py
    python scripts/add_to_reading_list.py --arxiv-id 2106.01234 --title "X" --why "Y"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import reading_list_file, resolve_workspace  # noqa: E402

HEADER = (
    "# 待读清单（READING_LIST）\n\n"
    "> 顺研究脉络（MEMORY.md 的卡点）检索 arXiv 的命中。新增按 arXiv id 去重、幂等。\n"
)
# 匹配文件里已记录的 arXiv id，用于去重
ARXIV_RE = re.compile(r"arxiv:\s*([A-Za-z0-9.\-/]+)", re.IGNORECASE)


class InputError(Exception):
    pass


def normalize_id(raw: str) -> str:
    s = str(raw).strip()
    s = re.sub(r"^arxiv:\s*", "", s, flags=re.IGNORECASE)
    return s.strip()


def existing_ids(text: str) -> set[str]:
    return {m.group(1).lower() for m in ARXIV_RE.finditer(text)}


def render_entry(arxiv_id: str, title: str, why: str) -> str:
    lines = [f"- **{title}** — arXiv:{arxiv_id}"]
    if why:
        lines.append(f"  - 为什么相关：{why}")
    return "\n".join(lines)


def read_stdin_or_file(input_arg: str | None) -> str:
    if input_arg in (None, "-"):
        return sys.stdin.read()
    path = Path(input_arg).expanduser()
    if not path.is_file():
        raise InputError(f"找不到输入文件：{path}")
    return path.read_text(encoding="utf-8")


def load_entries(args) -> list[dict]:
    if args.arxiv_id:  # 单条 CLI 优先
        return [{"arxiv_id": args.arxiv_id, "title": args.title or "", "why": args.why or ""}]
    raw = read_stdin_or_file(args.input)
    if not raw.strip():
        raise InputError("没有输入（既无 --arxiv-id，也无 stdin/--input 内容）。")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InputError(f"JSON 解析失败：{exc}")
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise InputError("输入 JSON 必须是对象或对象数组。")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="把 arXiv 命中幂等追加进 READING_LIST.md（不联网、不调大模型）"
    )
    parser.add_argument("--input", help="JSON 文件；缺省或 `-` 从 stdin 读")
    parser.add_argument("--arxiv-id", dest="arxiv_id", help="单条：arXiv id")
    parser.add_argument("--title", help="单条：标题")
    parser.add_argument("--why", help="单条：一句为什么相关")
    parser.add_argument("--workspace", help="覆盖 workspace 目录")
    args = parser.parse_args(argv)

    try:
        entries = load_entries(args)
    except InputError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 2

    workspace = resolve_workspace(args.workspace)
    path = reading_list_file(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)

    content = path.read_text(encoding="utf-8") if path.exists() else HEADER
    seen = existing_ids(content)  # 已在清单里的 id（去重基准）

    new_blocks: list[str] = []
    added: list[str] = []
    skipped: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            print("[错误] 每条命中必须是对象 {arxiv_id, title, why}。", file=sys.stderr)
            return 2
        aid = normalize_id(entry.get("arxiv_id", ""))
        title = str(entry.get("title", "")).strip()
        why = str(entry.get("why", "")).strip()
        if not aid:
            print("[错误] 某条命中缺少 arxiv_id。", file=sys.stderr)
            return 2
        if not title:
            print(f"[错误] arXiv:{aid} 缺少 title。", file=sys.stderr)
            return 2
        if aid.lower() in seen:  # 已存在 / 本批重复 → 幂等跳过
            skipped.append(aid)
            continue
        seen.add(aid.lower())
        new_blocks.append(render_entry(aid, title, why))
        added.append(aid)

    if new_blocks:
        has_entries = any(ln.startswith("- ") for ln in content.splitlines())
        sep = "\n" if has_entries else "\n\n"  # 首批与表头之间留空行，之后紧接成列表
        content = content.rstrip("\n") + sep + "\n".join(new_blocks) + "\n"
        path.write_text(content, encoding="utf-8")

    print(f"待读清单：新增 {len(added)}，跳过（已存在）{len(skipped)} → {path}")
    if added:
        print("  新增：" + ", ".join(f"arXiv:{a}" for a in added))
    if skipped:
        print("  跳过：" + ", ".join(f"arXiv:{a}" for a in skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
