from __future__ import annotations
import json
import urllib.request
from typing import Any

def _post_json(url: str, payload: dict) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "codegate-cli"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))

def authorize_pip_install(api_base: str, requirements: list[dict]) -> dict:
    if not api_base:
        raise RuntimeError("No api_base configured. Run: codegate activate --api ...")

    payload = {
        "ecosystem": "pypi",
        "requirements": requirements,  # [{name, version, raw}]
    }
    return _post_json(f"{api_base.rstrip('/')}/authorize", payload)
