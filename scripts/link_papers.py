#!/usr/bin/env python3
r"""结绳 — 给两篇论文之间加一条「关联」边并双向回写（机械活）。

职责：把 Agent 已经判定好的一条关系，机械地写进**两边**文件的「关联」字段，
并从每篇各自的视角描述正确。**不调用大模型、不联网、无 key。**
关系是否成立、属哪种类型，由 Agent 在外面判断完再调本脚本。

视角规则：
    - 无向关系（冲突 / 互补 / 可组合）：两边对称，都写 `⟷`，类型不变。
    - 有向关系（取代）：from 取代 to。
        · from 一侧写：`→ \`to\` （取代：…）`
        · to   一侧写：`← \`from\` （被取代：…）`

幂等：同一条边（同 target + 同视角类型）重复跑不重复添加；文件其它内容原样不动。
首次写入会移除「（暂无）」占位行。

用法：
    python scripts/link_papers.py --from-id A --to-id B --type 冲突 --note "平稳 vs 非平稳"
    python scripts/link_papers.py --from-id new --to-id old --type 取代 --note "更紧的界" --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _md import bullets, section_body  # noqa: E402
from _paths import papers_dir, resolve_workspace  # noqa: E402

PLACEHOLDER_PREFIX = "_（暂无"
RELATION_HEADING = "## 关联"
VALID_RELATIONS = ("冲突", "互补", "取代", "可组合")

# 每种关系在 from / to 两侧的（方向符号, 类型标签）
PERSPECTIVES = {
    "冲突": {"from": ("⟷", "冲突"), "to": ("⟷", "冲突")},
    "互补": {"from": ("⟷", "互补"), "to": ("⟷", "互补")},
    "可组合": {"from": ("⟷", "可组合"), "to": ("⟷", "可组合")},
    "取代": {"from": ("→", "取代"), "to": ("←", "被取代")},
}


def format_line(direction: str, target: str, label: str, note: str) -> str:
    """与 write_paper.py 的渲染保持完全一致。"""
    note_part = f"：{note}" if note else ""
    return f"- {direction} `{target}` （{label}{note_part}）"


def edge_exists(existing_bullets: list[str], target: str, label: str) -> bool:
    """该侧是否已有指向 target、且视角类型为 label 的边（与 note 无关，判等更稳）。"""
    target_token = f"`{target}`"
    for item in existing_bullets:
        if target_token in item and (f"（{label}）" in item or f"（{label}：" in item):
            return True
    return False


def plan_edge(path: Path, target: str, label: str, direction: str, note: str):
    """返回 (action, new_text_or_None, line)。action ∈ {'exists','added'}。不写盘。"""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    new_line = format_line(direction, target, label, note)

    # 已存在则幂等跳过
    if edge_exists(bullets(section_body(text, "关联")), target, label):
        return "exists", None, new_line

    # 定位「## 关联」段
    heading_idx = next((i for i, ln in enumerate(lines) if ln.strip() == RELATION_HEADING), None)
    if heading_idx is None:
        # 没有该段则在末尾补一个（防御性；正常 schema 不会发生）
        rebuilt = lines[:]
        if rebuilt and rebuilt[-1].strip():
            rebuilt.append("")
        rebuilt += [RELATION_HEADING, new_line]
        return "added", "\n".join(rebuilt).rstrip() + "\n", new_line

    end_idx = len(lines)
    for i in range(heading_idx + 1, len(lines)):
        if lines[i].lstrip().startswith("## "):
            end_idx = i
            break

    body = lines[heading_idx + 1:end_idx]
    tail = lines[end_idx:]

    # 去掉占位行，去掉段尾空行，再追加新边
    new_body = [ln for ln in body if not ln.strip().startswith(PLACEHOLDER_PREFIX)]
    while new_body and not new_body[-1].strip():
        new_body.pop()
    new_body.append(new_line)

    rebuilt = lines[:heading_idx + 1] + new_body + tail
    return "added", "\n".join(rebuilt).rstrip() + "\n", new_line


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="给两篇论文加一条关联边并双向回写（幂等，不联网、不调大模型）"
    )
    parser.add_argument("--from-id", required=True, dest="from_id", help="起点论文 id")
    parser.add_argument("--to-id", required=True, dest="to_id", help="终点论文 id")
    parser.add_argument("--type", required=True, choices=VALID_RELATIONS, help="关系类型")
    parser.add_argument("--note", default="", help="一句话说明（两侧共用）")
    parser.add_argument("--workspace", help="覆盖 workspace 目录")
    parser.add_argument("--dry-run", action="store_true", help="只显示将写入的内容，不落盘")
    args = parser.parse_args(argv)

    if args.from_id == args.to_id:
        print("[错误] from-id 与 to-id 相同，不能给论文连自身边。", file=sys.stderr)
        return 2

    workspace = resolve_workspace(args.workspace)
    pdir = papers_dir(workspace)
    from_path = pdir / f"{args.from_id}.md"
    to_path = pdir / f"{args.to_id}.md"

    for pid, p in ((args.from_id, from_path), (args.to_id, to_path)):
        if not p.is_file():
            print(f"[错误] 找不到论文文件：{p}（id={pid}）", file=sys.stderr)
            return 2

    persp = PERSPECTIVES[args.type]
    from_dir, from_label = persp["from"]
    to_dir, to_label = persp["to"]

    from_action, from_text, from_line = plan_edge(
        from_path, target=args.to_id, label=from_label, direction=from_dir, note=args.note
    )
    to_action, to_text, to_line = plan_edge(
        to_path, target=args.from_id, label=to_label, direction=to_dir, note=args.note
    )

    if args.dry_run:
        print("[dry-run] 不写盘，仅预览：")
        print(f"  {from_path.name}: [{from_action}] {from_line}")
        print(f"  {to_path.name}: [{to_action}] {to_line}")
        return 0

    if from_text is not None:
        from_path.write_text(from_text, encoding="utf-8")
    if to_text is not None:
        to_path.write_text(to_text, encoding="utf-8")

    if from_action == "exists" and to_action == "exists":
        print(f"边已存在（{args.type}），两边均未改动（幂等）。")
    else:
        print("已双向回写：")
        print(f"  {from_path.name}: [{from_action}] {from_line}")
        print(f"  {to_path.name}: [{to_action}] {to_line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
