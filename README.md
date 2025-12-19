# CodeGate CLI

[![PyPI version](https://badge.fury.io/py/codegate.svg)](https://badge.fury.io/py/codegate)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Security: Critical](https://img.shields.io/badge/Security-Critical-red)](https://codegate.com)

**The Supply Chain Firewall for AI Agents.**

CodeGate is a security toolkit designed to detect and prevent "Slopsquatting"—a new class of supply chain attack where malicious actors register non-existent packages that AI agents commonly hallucinate.

> **Note:** This CLI provides **static analysis** and **probing** capabilities. For real-time **kernel-level protection** (eBPF + MicroVMs), please request access to the [CodeGate Runtime Engine](mailto:jerryscout71@gmail.com).

## The Problem

AI coding agents (like ChatGPT, Copilot, or Claude) generate code at runtime. They often "hallucinate" package names that look real but do not exist on PyPI.

1. **Hallucination:** The AI writes `import langchain_community_pack`.
2. **Attack:** An attacker notices this common hallucination and registers `langchain_community_pack` on PyPI with malicious code.
3. **Compromise:** The AI agent executes `pip install`, downloading the malware immediately.

Static scanners (Snyk/GitHub) cannot catch this because the code is generated on the fly.

## Installation

```bash
pip install codegate
```

## Usage

### 1. Analyzer (scan)

Check your `requirements.txt` for "Shadow Dependencies"—packages that are either hallucinations (404) or suspiciously new (Dependency Confusion risk).

```bash
codegate scan requirements.txt
```

**What it checks:**

- Hallucinations: Packages that do not exist (high risk of future hijacking).
- Typosquatting: Packages with names dangerously similar to popular libraries.
- Freshness: Packages registered < 30 days ago.

### 2. Slopsquatting Prober (probe)

Actively probe your LLM to see if it is susceptible to suggesting malicious packages. This tool sends "honeytrap" prompts designed to force hallucinations.

```bash
codegate probe
```

**Custom Probing:**

```bash
codegate probe --prompt "I need a Python library to parse X-Financial-98 logs"
```

If the AI suggests a package that doesn't exist, CodeGate alerts you that your agent is vulnerable.

## The Runtime Engine (Beta)

The CLI detects the risk. The CodeGate Runtime Engine eliminates it.

While this CLI runs locally, our Engine sits as a transparent proxy between your AI Agents and the internet.

- **Isolation:** Every `pip install` runs inside an ephemeral Firecracker MicroVM.
- **Interception:** An eBPF probe at the kernel bridge (`br0`) inspects packet flow.
- **Enforcement:** Drops connections to unverified or hallucinated packages < 1ms before they execute.

[Request Access to Private Beta](mailto:jerryscout71@gmail.com)

## Architecture

The CodeGate CLI is built on two core modules:

- **The Crawler:** A high-speed PyPI metadata indexer that builds a local "Truth Graph" of valid dependencies.
- **The Solver:** A reimplementation of the pip resolution logic to identify deep nested dependency risks.

## Contributing

We are looking for contributions to expand the "Hallucination Graph"—our database of common fake packages AI agents suggest.

1. Fork the repo.
2. Add known hallucinations to `codegate/data/hallucinations.json`.
3. Submit a PR.

## License

MIT License. Copyright (c) 2025 CodeGate.

---
