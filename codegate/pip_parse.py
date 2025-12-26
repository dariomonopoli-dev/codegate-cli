from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

REQ_RE = re.compile(r"^[A-Za-z0-9_.-]+(\[.*\])?(==[A-Za-z0-9_.+-]+)?$")

DISALLOWED_TOKENS = {
    "-e", "--editable",
    "--no-index",
    "--find-links", "-f",
    "--index-url",
    "--extra-index-url",
}

@dataclass(frozen=True)
class Requirement:
    raw: str
    name: str
    version: str | None 

def _strip_comment(line: str) -> str:
    return line.split("#", 1)[0].strip()

def parse_simple_requirement(token: str) -> Requirement:
    token = token.strip()
    if not token:
        raise ValueError("Empty requirement")

    low = token.lower()
    if low.startswith(("git+", "http://", "https://", "ssh://", "file://")):
        raise ValueError(f"URL/VCS installs not supported in MVP: {token}")
    if token in {".", ".."} or token.startswith(("./", "../")):
        raise ValueError(f"Local path installs not supported in MVP: {token}")
    if not REQ_RE.match(token):
        raise ValueError(f"Unsupported requirement format in MVP: {token}")

    if "==" in token:
        name, ver = token.split("==", 1)
        name = name.split("[", 1)[0]
        return Requirement(raw=token, name=name, version=ver)

    name = token.split("[", 1)[0]
    return Requirement(raw=token, name=name, version=None)

def parse_requirements_file(path: Path) -> list[Requirement]:
    if not path.exists():
        raise ValueError(f"requirements file not found: {path}")
    out: list[Requirement] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = _strip_comment(line)
        if not s:
            continue
        if s.startswith(("-", "--")):
            first = s.split()[0]
            if first in DISALLOWED_TOKENS:
                raise ValueError(f"Blocked directive in requirements file (MVP): {s}")
            continue
        out.append(parse_simple_requirement(s))
    return out

def parse_pip_install_args(args: list[str]) -> list[Requirement]:
    """
    args = everything that comes after 'pip install'.
    Supports:
      - pkg / pkg==ver
      - -r requirements.txt
    Blocks:
      - -e, URL, git+, path locali, --no-index, --index-url, etc.
    """
    reqs: list[Requirement] = []
    i = 0
    while i < len(args):
        a = args[i]

        if a in DISALLOWED_TOKENS:
            raise ValueError(f"Blocked pip option in MVP: {a}")

        if a in ("-r", "--requirement"):
            if i + 1 >= len(args):
                raise ValueError("Missing file after -r/--requirement")
            reqs.extend(parse_requirements_file(Path(args[i + 1])))
            i += 2
            continue

        if a.startswith("-"):
            i += 1
            continue

        reqs.append(parse_simple_requirement(a))
        i += 1

    return reqs
