# scanner_server.py
from __future__ import annotations

import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import os
import re
import shutil
import subprocess
import tempfile
from typing import Optional, Tuple

SAFE_CHAIN_BIN = os.getenv("SAFE_CHAIN_BIN", "/Users/mondra/.safe-chain/bin/safe-chain")

print("=== LOADED scanner_server.py ===", __file__)

class IntelAPIError(RuntimeError):
    pass

app = FastAPI()

class Requirement(BaseModel):
    name: str
    version: Optional[str] = None
    raw: str

class AuthRequest(BaseModel):
    requirements: List[Requirement]

def pypi_exists(name: str) -> bool:
    url = f"https://pypi.org/pypi/{name}/json"
    try:
        r = requests.get(url, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _extract_block_reason(text: str) -> str:
    lines = text.splitlines()
    for line in reversed(lines):
        if "blocked by safe-chain" in line.lower():
            return line.strip()[:300]
    return "blocked by safe-chain"


def aikido_is_malware(name: str, version: Optional[str] = None) -> Tuple[bool, str]:
    bin_path = shutil.which(SAFE_CHAIN_BIN) or SAFE_CHAIN_BIN

    spec = f"{name}=={version}" if version else name
    with tempfile.TemporaryDirectory() as td:
        cmd = [bin_path, "pip", "download", "--no-deps", "-d", td, spec]
        p = subprocess.run(cmd, capture_output=True, text=True)

    out = ((p.stdout or "") + "\n" + (p.stderr or "")).lower()

    if p.returncode != 0 and "blocked by safe-chain" in out.lower():
        return (True, _extract_block_reason(out))

    return (False, "")


@app.post("/authorize/pip")
def authorize(req: AuthRequest):
    per_pkg = []
    for r in req.requirements:
        name = r.name.strip()

        if not pypi_exists(name):
            per_pkg.append({"name": name, "allow": False, "reason": "Not found on PyPI"})
            continue

        is_bad, reason = aikido_is_malware(name, r.version)
        if is_bad:
            per_pkg.append({"name": name, "allow": False, "reason": f"Flagged as malware: {reason}"})
            continue

        per_pkg.append({"name": name, "allow": True})

    denied = [x for x in per_pkg if x["allow"] is False]
    if denied:
        return {
            "allow": False,
            "reason": "One or more packages denied",
            "per_package": denied,
        }

    return {"allow": True}