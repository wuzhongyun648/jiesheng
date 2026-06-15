"""结绳 — 共享路径解析。

纯本地、跨平台（统一用 pathlib）。**记忆数据与技能代码解耦**：默认存在用户数据目录，
不再相对技能文件夹——这样重装 / 更新技能永远不碰记忆，也与具体运行时（QClaw / 原生 OpenClaw）解耦。

记忆数据路径可配置，优先级：
    (1) 命令行 --workspace
    (2) 环境变量 JIESHENG_WORKSPACE
    (3) 默认 ~/.jiesheng/workspace（用 Path.home()；Windows 即 C:\\Users\\<用户名>\\.jiesheng\\workspace）

走默认值时若目录不存在则自动创建。
"""
from __future__ import annotations

import os
from pathlib import Path

ENV_VAR = "JIESHENG_WORKSPACE"

# 固定的用户数据目录，独立于技能安装位置
DEFAULT_WORKSPACE = Path.home() / ".jiesheng" / "workspace"


def resolve_workspace(cli_value: str | None = None) -> Path:
    """解析 workspace 目录，遵循上面说明的优先级；走默认值时不存在就创建。"""
    if cli_value:
        return Path(cli_value).expanduser().resolve()
    env = os.environ.get(ENV_VAR)
    if env:
        return Path(env).expanduser().resolve()
    default = DEFAULT_WORKSPACE.expanduser().resolve()
    default.mkdir(parents=True, exist_ok=True)
    return default


def memory_file(workspace: Path) -> Path:
    """研究主干 MEMORY.md。"""
    return workspace / "MEMORY.md"


def papers_dir(workspace: Path) -> Path:
    """论文记忆目录 memory/papers/。"""
    return workspace / "memory" / "papers"


def outputs_dir(workspace: Path) -> Path:
    """产物目录 outputs/（related work 草稿等，非记忆真相源）。"""
    return workspace / "outputs"


def reading_list_file(workspace: Path) -> Path:
    """待读清单 READING_LIST.md。"""
    return workspace / "READING_LIST.md"
