#!/usr/bin/env python3
"""结绳 — 从 PDF 提取纯文本（机械活）。

职责：给一个 PDF 路径，吐出文本。**不调用大模型、不联网、无任何 key。**
语义工作（读、抽假设、下判断）由 Agent 按 SKILL.md 来做，本脚本只负责把字节变成文本。

用法：
    python scripts/extract_pdf.py <pdf路径>                 # 文本打印到 stdout
    python scripts/extract_pdf.py <pdf路径> --out out.txt   # 文本写入文件

后端：按顺序尝试 pypdf / PyPDF2 / pdfminer.six。三者都没装时，给出离线安装提示并以非零码退出
（脚本本身不会去联网装包）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _extract_with_pypdf(path: Path) -> str | None:
    """优先 pypdf，回退到旧名 PyPDF2。两者都没有则返回 None。"""
    try:
        from pypdf import PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader  # 旧包名
        except Exception:
            return None
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_with_pdfminer(path: Path) -> str | None:
    try:
        from pdfminer.high_level import extract_text as _pdfminer_extract
    except Exception:
        return None
    return _pdfminer_extract(str(path))


def extract_text(path: Path) -> str:
    for backend in (_extract_with_pypdf, _extract_with_pdfminer):
        text = backend(path)
        if text is not None:
            return text
    raise RuntimeError(
        "未找到可用的 PDF 解析后端。请先安装其一（离线环境请预先准备好）：\n"
        "    pip install pypdf\n"
        "  或  pip install pdfminer.six"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从 PDF 提取纯文本（不联网、不调大模型）")
    parser.add_argument("pdf", help="PDF 文件路径")
    parser.add_argument("--out", help="输出文本文件路径；缺省则打印到 stdout")
    args = parser.parse_args(argv)

    pdf_path = Path(args.pdf).expanduser()
    if not pdf_path.is_file():
        print(f"找不到 PDF 文件：{pdf_path}", file=sys.stderr)
        return 2

    try:
        text = extract_text(pdf_path)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"已写出文本：{out_path}（{len(text)} 字符）", file=sys.stderr)
    else:
        sys.stdout.write(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
