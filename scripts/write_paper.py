#!/usr/bin/env python3
"""结绳 — 把结构化字段写成 memory/papers/{id}.md（机械活）。

职责：接收 Agent 已经抽好的结构化字段（JSON），按 SPEC 第 4 节的 schema 渲染成 markdown 并落盘。
**不调用大模型、不联网、无任何 key。** 语义工作（读论文、抽假设、下判断）由 Agent 在外面做完。

字段级硬约束（不靠模型自觉，由本脚本强制）：
    - 每条「核心假设」「关键结论」必须带 `[原文 …]` 标签（客观摘录、可回原文核对）。
    - 每条「我的判断」必须带 `[推断]` 标签。
    缺标签即报错、拒绝写入。

输入 JSON（从 stdin 或 --input 文件读）：
    {
      "id": "linear-bandit-2011",                 # 必填，kebab-case，作文件名
      "title": "Improved Algorithms for ...",     # 必填
      "source": "Abbasi-Yadkori et al. · NeurIPS 2011",  # 必填（出处）
      "hypotheses": ["reward 平稳（θ* 固定） [原文 §1]"],   # 核心假设，每条带 [原文 …]
      "conclusions": ["... [原文 §4]"],            # 关键结论，每条带 [原文 …]
      "judgments": ["... [推断]"],                 # 我的判断，每条带 [推断]
      "relations": [                              # 关联（B1 通常留空；冲突检测/回写见 B2）
        {"target": "ppr-dynamic-2016", "type": "冲突",
         "note": "平稳 vs 非平稳", "direction": "⟷"}
      ]
    }

用法：
    python scripts/write_paper.py --input paper.json
    cat paper.json | python scripts/write_paper.py
    python scripts/write_paper.py --input paper.json --print   # 只预览渲染结果，不写盘
    python scripts/write_paper.py --input paper.json --force    # 允许覆盖已存在文件
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 让脚本无论从哪个 cwd 调用都能找到同目录的 _paths
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import papers_dir, resolve_workspace  # noqa: E402

SOURCE_TAG = "[原文"          # 客观摘录标签前缀（带章节号，如 [原文 §4]）
JUDGMENT_TAG = "[推断]"       # 推断标签
VALID_RELATIONS = ("冲突", "互补", "取代", "可组合")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class ValidationError(Exception):
    """字段校验失败。"""


def _as_list(value, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError(f"字段 `{field}` 必须是字符串数组。")
    items = [str(v).strip() for v in value]
    return [v for v in items if v]


def _require_tag(items: list[str], tag: str, field: str) -> None:
    for item in items:
        if tag not in item:
            raise ValidationError(
                f"字段 `{field}` 的这条缺少 `{tag}` 标签（字段级硬约束，必须可溯源）：\n    {item}"
            )


def validate(data: dict) -> dict:
    paper_id = str(data.get("id", "")).strip()
    if not paper_id:
        raise ValidationError("缺少必填字段 `id`。")
    if not ID_PATTERN.match(paper_id):
        raise ValidationError(
            f"`id` 不合法：{paper_id!r}。请用 kebab-case（小写字母/数字/`-._`，不含路径分隔符）。"
        )

    title = str(data.get("title", "")).strip()
    if not title:
        raise ValidationError("缺少必填字段 `title`。")

    source = str(data.get("source", "")).strip()
    if not source:
        raise ValidationError("缺少必填字段 `source`（出处）。")

    hypotheses = _as_list(data.get("hypotheses"), "hypotheses")
    conclusions = _as_list(data.get("conclusions"), "conclusions")
    judgments = _as_list(data.get("judgments"), "judgments")

    # 字段级硬约束：来源摘录必须可溯源，判断必须自标
    _require_tag(hypotheses, SOURCE_TAG, "hypotheses")
    _require_tag(conclusions, SOURCE_TAG, "conclusions")
    _require_tag(judgments, JUDGMENT_TAG, "judgments")

    relations = []
    raw_relations = data.get("relations") or []
    if not isinstance(raw_relations, list):
        raise ValidationError("字段 `relations` 必须是数组。")
    for rel in raw_relations:
        if not isinstance(rel, dict):
            raise ValidationError("`relations` 的每项必须是对象 {target, type, note, direction}。")
        target = str(rel.get("target", "")).strip()
        rel_type = str(rel.get("type", "")).strip()
        if not target:
            raise ValidationError("`relations` 某项缺少 `target`（目标论文 id）。")
        if rel_type not in VALID_RELATIONS:
            raise ValidationError(
                f"`relations` 的 `type` 必须是 {VALID_RELATIONS} 之一，收到：{rel_type!r}。"
            )
        relations.append({
            "target": target,
            "type": rel_type,
            "note": str(rel.get("note", "")).strip(),
            "direction": str(rel.get("direction", "")).strip() or "⟷",
        })

    return {
        "id": paper_id,
        "title": title,
        "source": source,
        "hypotheses": hypotheses,
        "conclusions": conclusions,
        "judgments": judgments,
        "relations": relations,
    }


def render(paper: dict) -> str:
    lines: list[str] = [f"# {paper['title']}", "", f"**出处**: {paper['source']}", ""]

    def section(heading: str, items: list[str]) -> None:
        lines.append(f"## {heading}")
        if items:
            lines.extend(f"- {item}" for item in items)
        else:
            lines.append("_（暂无）_")
        lines.append("")

    section("核心假设", paper["hypotheses"])
    section("关键结论", paper["conclusions"])
    section("我的判断", paper["judgments"])

    lines.append("## 关联")
    if paper["relations"]:
        for rel in paper["relations"]:
            note = f"：{rel['note']}" if rel["note"] else ""
            lines.append(f"- {rel['direction']} `{rel['target']}` （{rel['type']}{note}）")
    else:
        lines.append("_（暂无；冲突检测与关联回写见 B2）_")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def read_input(input_arg: str | None) -> str:
    if input_arg in (None, "-"):
        return sys.stdin.read()
    path = Path(input_arg).expanduser()
    if not path.is_file():
        raise ValidationError(f"找不到输入文件：{path}")
    return path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="把结构化论文字段写成 memory/papers/{id}.md（不联网、不调大模型）"
    )
    parser.add_argument("--input", help="输入 JSON 文件路径；缺省或 `-` 时从 stdin 读")
    parser.add_argument("--workspace", help="覆盖 workspace 目录（默认 $JIESHENG_WORKSPACE 或 ~/.jiesheng/workspace）")
    parser.add_argument("--print", dest="print_only", action="store_true",
                        help="只打印渲染结果，不写盘")
    parser.add_argument("--force", action="store_true", help="允许覆盖已存在的论文文件")
    args = parser.parse_args(argv)

    try:
        raw = read_input(args.input)
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValidationError("输入 JSON 顶层必须是对象 {...}。")
        paper = validate(data)
    except ValidationError as exc:
        print(f"[校验失败] {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"[JSON 解析失败] {exc}", file=sys.stderr)
        return 2

    markdown = render(paper)

    if args.print_only:
        sys.stdout.write(markdown)
        return 0

    workspace = resolve_workspace(args.workspace)
    out_dir = papers_dir(workspace)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{paper['id']}.md"

    if out_path.exists() and not args.force:
        print(
            f"[已存在] {out_path}\n"
            f"  改已有文档属高风险动作：确认要覆盖请加 --force（关联回写交给 B2，不要在这里手动覆盖）。",
            file=sys.stderr,
        )
        return 3

    out_path.write_text(markdown, encoding="utf-8")
    print(f"已写入：{out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
