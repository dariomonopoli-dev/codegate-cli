"""
Codegate CLI.

Security guardrails for AI agents and package installation.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("codegate-cli")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["__version__"]
