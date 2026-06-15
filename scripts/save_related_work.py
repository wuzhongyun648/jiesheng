#!/usr/bin/env python3
"""结绳 — 把 Agent 写好的 related work 对比稿落盘到 workspace/outputs/（机械活）。

**不调用大模型、不联网、无 key。** 对比内容（带 `[原文 §x]` / `[推断]`、各条出处）由 Agent 在外面
写好，本脚本只负责把文本写到 workspace/outputs/{name}（默认 related_work_draft.md），按需建目录。
草稿是产物（非记忆真相源），默认允许覆盖——重写一版很正常。

用法：
    python scripts/save_related_work.py --input draft.md
    cat draft.md | python scripts/save_related_work.py
    python scripts/save_related_work.py --input draft.md --name related_work_v2.md
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import outputs_dir, resolve_workspace  # noqa: E402

DEFAULT_NAME = "related_work_draft.md"


def read_input(input_arg: str | None) -> str:
    if input_arg in (None, "-"):
        return sys.stdin.read()
    path = Path(input_arg).expanduser()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def _safe_name(name: str) -> bool:
    if not name or name in (".", ".."):
        return False
    if os.sep in name or (os.altsep and os.altsep in name) or "/" in name:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="把 related work 草稿写到 workspace/outputs/（不联网、不调大模型）"
    )
    parser.add_argument("--input", help="草稿内容文件；缺省或 `-` 从 stdin 读")
    parser.add_argument("--name", default=DEFAULT_NAME, help=f"输出文件名（默认 {DEFAULT_NAME}）")
    parser.add_argument("--workspace", help="覆盖 workspace 目录")
    args = parser.parse_args(argv)

    if not _safe_name(args.name):
        print(f"[错误] 非法文件名：{args.name!r}（不能含路径分隔符或 `..`）", file=sys.stderr)
        return 2

    try:
        content = read_input(args.input)
    except FileNotFoundError as exc:
        print(f"[错误] 找不到输入文件：{exc}", file=sys.stderr)
        return 2

    if not content.strip():
        print("[错误] 草稿内容为空，拒绝写入。", file=sys.stderr)
        return 2

    workspace = resolve_workspace(args.workspace)
    out_dir = outputs_dir(workspace)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.name

    text = content if content.endswith("\n") else content + "\n"
    out_path.write_text(text, encoding="utf-8")
    print(f"已写入：{out_path}（{len(text)} 字符）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
