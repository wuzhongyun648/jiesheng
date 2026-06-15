#!/usr/bin/env python3
"""结绳 — 打印解析出的 workspace 绝对路径（机械活）。

职责：按与所有脚本**完全相同**的优先级（`--workspace` > `$JIESHENG_WORKSPACE` >
`~/.jiesheng/workspace`）解析出 workspace，把**绝对路径**打到 stdout。
**不调用大模型、不联网、无 key。**

用途：Agent 在用自己的读写文件工具碰记忆前，先跑它拿到与脚本同源的绝对路径，
避免用裸相对路径 `workspace/…`——那会相对运行时 CWD（QClaw 即 `~/.qclaw/`）解析、
落进 `~/.qclaw/workspace/` 与脚本脑裂。

stdout 只有一行绝对路径，便于命令替换：
    WS=$(python scripts/print_workspace.py)

用法：
    python scripts/print_workspace.py            # 打印 workspace 绝对路径
    python scripts/print_workspace.py --all      # 连同 MEMORY.md / papers / outputs / READING_LIST 一起列
    python scripts/print_workspace.py --workspace /path/to/ws
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import (  # noqa: E402
    memory_file,
    outputs_dir,
    papers_dir,
    reading_list_file,
    resolve_workspace,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="打印解析出的 workspace 绝对路径（优先级与所有脚本一致；不联网、不调大模型）"
    )
    parser.add_argument(
        "--workspace",
        help="覆盖 workspace 目录（默认 $JIESHENG_WORKSPACE 或 ~/.jiesheng/workspace）",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="额外把 MEMORY.md / papers / outputs / READING_LIST 的绝对路径打到 stderr",
    )
    args = parser.parse_args(argv)

    workspace = resolve_workspace(args.workspace)

    # 绝对路径打到 stdout，单独一行，便于 $(...) 取用
    print(str(workspace))

    if args.all:
        # 派生路径打到 stderr，不污染 stdout 的单行契约
        for label, path in (
            ("MEMORY.md", memory_file(workspace)),
            ("papers/", papers_dir(workspace)),
            ("outputs/", outputs_dir(workspace)),
            ("READING_LIST.md", reading_list_file(workspace)),
        ):
            sys.stderr.write(f"{label}\t{path}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
