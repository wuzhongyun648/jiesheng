"""结绳 — 共享 markdown 只读 helper。

纯本地、跨平台（pathlib）。只负责把 memory/papers/{id}.md 读成结构，
**不解读语义**（语义比对由 Agent 做）。被 list_papers.py / link_papers.py 复用。

约定的文件结构（见 write_paper.py 渲染 / SPEC 第 4 节）：
    # 标题
    **出处**: ...
    ## 核心假设
    - ... [原文 §x]
    ## 关键结论
    - ...
    ## 我的判断
    - ... [推断]
    ## 关联
    - ⟷ `other-id` （冲突：一句话）
"""
from __future__ import annotations

from pathlib import Path

PLACEHOLDER_PREFIX = "_（暂无"  # write_paper.py 写空字段时的占位


def extract_title(text: str) -> str:
    """取第一个一级标题（`# `）作为论文标题。"""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return ""


def section_body(text: str, heading: str) -> list[str]:
    """返回 `## {heading}` 到下一个 `## ` 或文件末尾之间的原始行（不含标题行）。"""
    out: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.strip() == f"## {heading}":
            in_section = True
            continue
        if in_section and line.lstrip().startswith("## "):
            break
        if in_section:
            out.append(line)
    return out


def bullets(body_lines: list[str]) -> list[str]:
    """从一段 body 里取出 bullet 文本（去掉前导 `- `），跳过空行与占位行。"""
    items: list[str] = []
    for line in body_lines:
        s = line.strip()
        if not s or s.startswith(PLACEHOLDER_PREFIX):
            continue
        if s.startswith("- "):
            items.append(s[2:].strip())
    return items


def iter_paper_files(papers_dir: Path) -> list[Path]:
    """按文件名排序列出 papers 目录下的 *.md。"""
    if not papers_dir.is_dir():
        return []
    return sorted(p for p in papers_dir.glob("*.md") if p.is_file())
