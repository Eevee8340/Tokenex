# Tokenex — AI Editor Token Calculator

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A unified CLI tool to scan and report token usage across multiple AI-powered code editors.

## Supported Editors

| Editor       | Detection Method                        |
| ------------ | --------------------------------------- |
| Opencode     | `~/.local/share/opencode/opencode.db`   |
| Codex        | `~/.codex/state_5.sqlite`               |
| Gemini CLI   | `~/.gemini/tmp/*/chats/`                |
| Antigravity  | `~/.gemini/antigravity/brain/`          |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Launch the interactive menu:

```bash
python tokenex.py
```

### CLI Flags

| Flag | Description |
| ---- | ----------- |
| `--since YYYY-MM-DDTHH:MM:SS` | Filter scans after this datetime |
| `--until YYYY-MM-DDTHH:MM:SS` | Filter scans before this datetime |

## Features

- **Auto-detection** — Automatically finds installed editors by scanning known data paths
- **Interactive menu** — Choose individual editors or view all at once
- **Time-series charts** — Visualize token usage grouped by day, week, or month
- **Export** — Save results as JSON or CSV to `~/.tokenex/exports/`
- **History** — Track scan history with delta comparisons
- **Settings** — Configure custom paths for non-standard installations
