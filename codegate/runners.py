from __future__ import annotations
import os
import shutil
import subprocess
import sys

from codegate.config import load_config
from codegate.pip_parse import parse_pip_install_args
from codegate.shims import shim_dir
from urllib import request, error
from typing import Any

import json
from importlib import resources

def load_hallucinations() -> dict[str, dict]:
    """
    Returns map: normalized_name -> entry
    """
    data = resources.files("codegate").joinpath("data/hallucinations.json").read_text(encoding="utf-8")
    items = json.loads(data)
    out = {}
    for it in items:
        name = (it.get("name") or "").strip().lower()
        if name:
            out[name] = it
    return out

HALLU = load_hallucinations()

def _blocked_by_hallu(req_name: str) -> dict | None:
    return HALLU.get(req_name.strip().lower())

SHIM_DIR = str(shim_dir())


def _find_real_binary(name: str) -> str:
    """
    Find the real binary (pip) excluding the shim dir.
    So if you are in a venv, it will use the venv pip (which is still in the PATH).
    """
    paths = os.environ.get("PATH", "").split(os.pathsep)
    filtered = [p for p in paths if os.path.abspath(p) != os.path.abspath(SHIM_DIR)]
    real = shutil.which(name, path=os.pathsep.join(filtered))
    if not real:
        raise RuntimeError(f"Could not find real '{name}' in PATH (excluding shim dir).")
    return real

def _exec(binary: str, args: list[str]) -> int:
    return subprocess.call([binary, *args])

def main() -> int:
    # invoked as: python3 -m codegate.runners pip <args...>
    if len(sys.argv) < 2:
        print("Usage: python3 -m codegate.runners pip <args...>", file=sys.stderr)
        return 2

    tool = sys.argv[1]
    args = sys.argv[2:]

    if tool != "pip":
        print(f"Unknown tool: {tool}", file=sys.stderr)
        return 2

    return run_pip(args)

def _authorize_pip_install(api_base: str, requirements: list[dict[str, Any]], timeout_s: float = 5.0) -> dict[str, Any]:
    api_base = (api_base or "").strip()
    if not api_base:
        raise RuntimeError("scanner api_base is empty")

    url = api_base.rstrip("/") + "/authorize/pip"
    print("[codegate] scanner url:", url, file=sys.stderr)
    payload = json.dumps({"requirements": requirements}).encode("utf-8")

    req = request.Request(
        url=url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace").strip()
    except error.HTTPError as e:
        try:
            msg = e.read().decode("utf-8", errors="replace")
        except Exception:
            msg = e.reason
        raise RuntimeError(f"scanner HTTP {e.code}: {msg}")
    except error.URLError as e:
        raise RuntimeError(str(e))

    try:
        data = json.loads(body) if body else {}
    except Exception:
        raise RuntimeError(f"scanner returned non-JSON: {body[:200]}")

    if not isinstance(data, dict) or "allow" not in data:
        raise RuntimeError(f"scanner returned invalid response: {body[:200]}")

    return data

def run_pip(args: list[str]) -> int:
    print("[codegate] runners file:", __file__, file=sys.stderr)
    cfg = load_config()
    api_base = str(cfg.get("api_base", "")).strip()
    fail_open = bool(cfg.get("fail_open", False))


    real_pip = _find_real_binary("pip")

    if not args:
        return _exec(real_pip, args)

    subcmd = args[0]
    print("[codegate] pip argv:", args, file=sys.stderr)
    print("[codegate] api_base:", api_base, "fail_open:", fail_open, file=sys.stderr)

    if subcmd != "install":
        return _exec(real_pip, args)

    install_args = args[1:]

    try:
        reqs = parse_pip_install_args(install_args)
        print("[codegate] parsed reqs:", [getattr(r, "raw", None) for r in reqs], file=sys.stderr)

    except Exception as e:
        print(f"Blocked (unsupported pip install pattern in MVP): {e}", file=sys.stderr)
        return 1

    # if no requirements (only flags), pass-through
    if not reqs:
        return _exec(real_pip, args)
    
    # hard-block known hallucinations/slopsquats first
    blocked = []
    for r in reqs:
        hit = _blocked_by_hallu(r.name)
        if hit:
            blocked.append(hit)

    if blocked:
        print("Blocked by Codegate (known hallucination):", file=sys.stderr)
        for b in blocked:
            print(f"  , {b['name']} ({b.get('risk_level','unknown')}): {b.get('reason','')}", file=sys.stderr)
        return 1

    try:
        print("[codegate] BEFORE_SCANNER", file=sys.stderr)
        sys.stderr.flush()

        decision = _authorize_pip_install(
            api_base=api_base,
            requirements=[{"name": r.name, "version": r.version, "raw": r.raw} for r in reqs],
        )
        print("[codegate] scanner decision:", decision, file=sys.stderr)


    except Exception as e:
        print(f"[codegate] scanner error: {e}", file=sys.stderr)
        if fail_open:
            return _exec(real_pip, args)
        print(f"Blocked: scanner error ({e}).", file=sys.stderr)
        return 1

    if bool(decision.get("allow", False)):


        extra = decision.get("extra_pip_args") or []
        if not isinstance(extra, list):
            extra = []
        return _exec(real_pip, [*args, *extra])

    reason = decision.get("reason") or "Denied by policy"
    print(f"Blocked by policy: {reason}", file=sys.stderr)

    per_pkg = decision.get("per_package")
    if isinstance(per_pkg, list):
        for item in per_pkg:
            if item.get("allow") is False:
                name = item.get("name", "?")
                r = item.get("reason", "")
                print(f"  , {name}: {r}".rstrip(), file=sys.stderr)

    return 1

if __name__ == "__main__":
    raise SystemExit(main())
