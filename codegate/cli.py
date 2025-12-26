from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from codegate.config import load_config, save_config
from codegate.shims import install_pip_shims, remove_pip_shims, shim_dir, shim_first_in_path, shim_dir, install_codegate_launcher


def _shell_rc_hint() -> str:
    shell = os.environ.get("SHELL", "")
    if shell.endswith("zsh"):
        return "~/.zshrc"
    if shell.endswith("bash"):
        return "~/.bashrc"
    return "your shell rc file (e.g. ~/.zshrc)"

def _which(cmd: str) -> str | None:
    return shutil.which(cmd)

def main():
    p = argparse.ArgumentParser(prog="codegate")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("activate", help="Install pip shims + configure scanner endpoint")
    a.add_argument("--api", default="http://localhost:8080", help="Scanner API base URL")
    a.add_argument("--strict", action="store_true", help="Fail closed if scanner is unreachable (recommended for CI)")

    sub.add_parser("status", help="Show config and shim presence")
    sub.add_parser("doctor", help="Verify that pip is intercepted")
    sub.add_parser("deactivate", help="Remove shims (manual PATH cleanup if you added it)")

    # dentro main() in codegate/cli.py

    r = sub.add_parser("run", help="Run a command with Codegate shims enabled (PATH is modified for this process only)")
    r.add_argument("--", dest="dashdash", action="store_true", help=argparse.SUPPRESS)
    r.add_argument("command", nargs=argparse.REMAINDER, help="Command to run, e.g. -- pip install requests")


    args = p.parse_args()

    if args.cmd == "activate":
        cfg = load_config()
        cfg["api_base"] = args.api
        cfg["fail_open"] = (not bool(args.strict))
        save_config(cfg)

        paths = install_pip_shims()
        paths.append(install_codegate_launcher())
        print("Installed shims:")
        for sp in paths:
            print("  ,", sp)
        

    elif args.cmd == "status":
        cfg = load_config()
        print("Config:", cfg)
        print("Shim dir:", shim_dir())
        print("Shims present:")
        cg = shim_dir() / "codegate"
        if cg.exists():
            try:
                first = cg.read_text(encoding="utf-8").splitlines()
                # find the line that contains -m codegate.cli
                line = next((l for l in first if " -m codegate.cli " in l or " -m codegate.cli" in l), "")
                print("Shim python:", line.strip() or "(could not detect)")
            except Exception as e:
                print("Shim python: (error reading shim)", e)
        else:
            print("Shim python: (codegate shim missing)")

        for name in ("pip", "pip3"):
            print(f"  , {name}: {'YES' if (shim_dir()/name).exists() else 'NO'}")
        print("Shim first in PATH:", "YES" if shim_first_in_path() else "NO")

    elif args.cmd == "doctor":
        print("=== CODEGATE DOCTOR ===")

        # 1) shims exist?
        missing = []
        for name in ("pip", "pip3", "codegate"):
            pth = shim_dir() / name
            ok = pth.exists()
            print(f"  , {name}: {'OK' if ok else 'MISSING'} ({pth})")
            if not ok:
                missing.append(name)

        if missing:
            print("\nFix: run `codegate activate`")
            return

        # 2) does codegate-run path injection work?
        try:
            env = os.environ.copy()
            env["PATH"] = f"{shim_dir()}:{env.get('PATH','')}"
            resolved = subprocess.check_output(["sh", "-lc", "command -v pip"], env=env, text=True).strip()
            print("\n`codegate run` will resolve pip to:")
            print("  ,", resolved)

            expected = os.path.abspath(str(shim_dir() / "pip"))
            if os.path.abspath(resolved) == expected:
                print("\n✅ OK: `codegate run -- pip ...` is protected.")
            else:
                print("\n⚠️ Warning: pip does not resolve to the shim under codegate-run.")
                print("   This is unexpected. Try re-running `codegate activate`.")
        except Exception as e:
            print("\n⚠️ Warning: could not run self-check:", e)

        print("\nUsage:")
        print("  codegate run -- <command>")
        print("Example:")
        print("  codegate run -- pip install requests")



    elif args.cmd == "deactivate":
        removed = remove_pip_shims()
        print(f"Removed {removed} shim(s) from {shim_dir()}")
        print("If you added PATH in your shell rc, remove that line manually.")

    elif args.cmd == "run":
        

        cmd = args.command
        if cmd and cmd[0] == "--":
            cmd = cmd[1:]
        if not cmd:
            print("Usage: codegate run -- <command...>", file=sys.stderr)
            raise SystemExit(2)

        env = os.environ.copy()
        env["PATH"] = f"{shim_dir()}:{env.get('PATH','')}"
        raise SystemExit(subprocess.call(cmd, env=env))

if __name__ == "__main__":
    main()