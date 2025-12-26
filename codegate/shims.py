from __future__ import annotations

import os
import stat
import sys
import shutil
from pathlib import Path

import shutil

def _python_abs() -> str:
    exe = sys.executable or "python3"
    if os.path.isabs(exe):
        return exe
    found = shutil.which(exe) or shutil.which("python3")
    return os.path.abspath(found) if found else exe


def shim_dir() -> Path:
    return Path.home() / ".codegate" / "bin"

def _write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

def _python_abs() -> str:
    exe = sys.executable or "python3"
    if os.path.isabs(exe):
        return exe
    found = shutil.which(exe) or shutil.which("python3") or exe
    return os.path.abspath(found)

def install_pip_shims() -> list[Path]:
    py = _python_abs()
    shim = f"""#!/usr/bin/env bash
set -euo pipefail
"{py}" -m codegate.runners pip "$@"
"""
    out = []
    for name in ("pip", "pip3"):
        p = shim_dir() / name
        _write_executable(p, shim)
        out.append(p)
    return out

def install_codegate_launcher() -> Path:
    py = _python_abs()
    launcher = f"""#!/usr/bin/env bash
set -euo pipefail
"{py}" -m codegate.cli "$@"
"""
    p = shim_dir() / "codegate"
    _write_executable(p, launcher)
    return p

def remove_pip_shims() -> int:
    removed = 0
    for name in ("pip", "pip3", "codegate"):
        p = shim_dir() / name
        if p.exists():
            p.unlink()
            removed += 1
    return removed

def shim_first_in_path() -> bool:
    d = os.path.abspath(str(shim_dir()))
    parts = [os.path.abspath(p) for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    return bool(parts) and parts[0] == d
