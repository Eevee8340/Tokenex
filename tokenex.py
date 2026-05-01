#!/usr/bin/env python3
"""Tokenex — Unified AI Editor Token Usage Calculator"""

import sys
import argparse
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import inquirer

from detectors import (
    OpencodeDetector,
    CodexDetector,
    GeminiCLIDetector,
    AntigravityDetector,
)
from utils import (
    load_config,
    save_config,
    display_editor_stats,
    display_comparison,
    export_json,
    export_csv,
    save_history_entry,
    get_last_entry,
    display_history,
    load_history,
)
from utils.charts import (
    display_time_series,
    _history_as_timeline,
)

console = Console()

ALL_DETECTORS = [
    OpencodeDetector,
    CodexDetector,
    GeminiCLIDetector,
    AntigravityDetector,
]


def get_custom_path(cfg, key):
    path_str = cfg.get(key)
    if path_str:
        return Path(path_str)
    return None


def detect_editors(cfg) -> dict:
    """Returns mapping of editor name -> detector instance for detected editors."""
    detected = {}
    for cls in ALL_DETECTORS:
        custom = get_custom_path(cfg, {
            "Opencode": "opencode_db_path",
            "Codex": "codex_db_path",
            "Gemini CLI": "gemini_cli_tmp_dir",
            "Antigravity": "antigravity_brain_dir",
        }.get(cls.name))
        inst = cls(custom_path=custom)
        if inst.detect():
            detected[cls.name] = inst
    return detected


def prompt_menu(choices):
    questions = [
        inquirer.List(
            "choice",
            message="Select an option",
            choices=choices,
        )
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        return None
    return answers["choice"]


def scan_editor(editor_name: str, detector, since=None, until=None) -> dict:
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task(f"[cyan]Scanning {editor_name}...", total=None)
        stats = detector.scan(since=since, until=until)
    return stats


def export_prompt(editor_name: str, stats: dict):
    questions = [
        inquirer.List(
            "format",
            message="Export format",
            choices=["JSON", "CSV", "Skip"],
        )
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        return
    fmt = answers["format"]
    if fmt == "JSON":
        path = export_json(editor_name, stats)
        console.print(f"[green]Exported to {path}[/green]")
    elif fmt == "CSV":
        path = export_csv(editor_name, stats)
        console.print(f"[green]Exported to {path}[/green]")


def settings_menu(cfg):
    console.print("\n[bold cyan]Settings[/bold cyan]")
    console.print("Current custom paths (None = auto-detect):")
    console.print(f"  Opencode DB: {cfg.get('opencode_db_path')}")
    console.print(f"  Codex DB: {cfg.get('codex_db_path')}")
    console.print(f"  Gemini CLI tmp: {cfg.get('gemini_cli_tmp_dir')}")
    console.print(f"  Antigravity brain: {cfg.get('antigravity_brain_dir')}")

    questions = [
        inquirer.List(
            "setting",
            message="Configure path for",
            choices=[
                "Opencode DB",
                "Codex DB",
                "Gemini CLI tmp dir",
                "Antigravity brain dir",
                "Back",
            ],
        )
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        return cfg
    choice = answers["setting"]
    if choice == "Back":
        return cfg

    key_map = {
        "Opencode DB": "opencode_db_path",
        "Codex DB": "codex_db_path",
        "Gemini CLI tmp dir": "gemini_cli_tmp_dir",
        "Antigravity brain dir": "antigravity_brain_dir",
    }
    key = key_map[choice]
    current = cfg.get(key) or ""
    path_q = [inquirer.Text("path", message=f"Enter full path (blank to clear, current: {current})", default="")]
    path_ans = inquirer.prompt(path_q)
    if path_ans:
        val = path_ans["path"].strip()
        if val:
            cfg[key] = val
        else:
            cfg.pop(key, None)
        save_config(cfg)
        console.print("[green]Settings saved.[/green]")
    return cfg


def show_deltas(editor_name: str, stats: dict):
    last = get_last_entry(editor_name)
    if not last:
        return
    delta_total = stats.get("total_processed", 0) - last.get("total_processed", 0)
    delta_input = stats.get("input", 0) - last.get("input", 0)
    delta_output = stats.get("output", 0) - last.get("output", 0)
    if delta_total or delta_input or delta_output:
        console.print(f"[dim]Change since last scan:[/dim]  Total: {delta_total:+,}  Input: {delta_input:+,}  Output: {delta_output:+,}")


def main():
    parser = argparse.ArgumentParser(description="Tokenex — AI Editor Token Calculator")
    parser.add_argument("--since", type=lambda s: datetime.fromisoformat(s), help="ISO datetime YYYY-MM-DDTHH:MM:SS")
    parser.add_argument("--until", type=lambda s: datetime.fromisoformat(s), help="ISO datetime YYYY-MM-DDTHH:MM:SS")
    args = parser.parse_args()

    cfg = load_config()
    detected = detect_editors(cfg)

    if not detected:
        console.print("[bold red]No AI editor data detected on this system.[/bold red]")
        console.print("[dim]You can set custom paths in Settings.[/dim]")

    while True:
        console.print("\n")
        menu_items = []
        for name in detected:
            menu_items.append(f"📊  {name}")
        if detected:
            menu_items.append("📊  Show All")
        menu_items.extend([
            "📈  Time-Series",
            "📁  Export Last Run",
            "🕘  View History",
            "⚙️   Settings",
            "❌  Exit",
        ])

        choice = prompt_menu(menu_items)
        if choice is None:
            break

        plain = choice.replace("📊  ", "").replace("📈  ", "").replace("📁  ", "").replace("🕘  ", "").replace("⚙️   ", "").replace("❌  ", "").strip()

        last_stats = {}

        if plain in detected:
            stats = scan_editor(plain, detected[plain], since=args.since, until=args.until)
            display_editor_stats(plain, stats)
            show_deltas(plain, stats)
            save_history_entry(plain, stats)
            last_stats = {plain: stats}
            export_prompt(plain, stats)

        elif plain == "Show All":
            all_stats = {}
            for name, detector in detected.items():
                stats = scan_editor(name, detector, since=args.since, until=args.until)
                display_editor_stats(name, stats)
                show_deltas(name, stats)
                save_history_entry(name, stats)
                all_stats[name] = stats
            display_comparison(all_stats)
            last_stats = all_stats
            # Export prompt for all (just aggregate)
            questions = [
                inquirer.List(
                    "fmt",
                    message="Export aggregate comparison",
                    choices=["JSON", "CSV", "Skip"],
                )
            ]
            ans = inquirer.prompt(questions)
            if ans and ans["fmt"] != "Skip":
                for name, stats in all_stats.items():
                    if ans["fmt"] == "JSON":
                        path = export_json(name, stats)
                        console.print(f"[green]Exported {name} to {path}[/green]")
                    else:
                        path = export_csv(name, stats)
                        console.print(f"[green]Exported {name} to {path}[/green]")

        elif plain == "Time-Series":
            if not detected:
                console.print("[yellow]No editors detected.[/yellow]")
                continue
            editor_q = [inquirer.List("editor", message="Select editor", choices=list(detected.keys()))]
            editor_ans = inquirer.prompt(editor_q)
            if not editor_ans:
                continue
            selected_editor = editor_ans["editor"]

            group_q = [inquirer.List("group", message="Group by", choices=["Day", "Week", "Month"])]
            group_ans = inquirer.prompt(group_q)
            if not group_ans:
                continue
            group_by = group_ans["group"]

            stats = scan_editor(selected_editor, detected[selected_editor], since=args.since, until=args.until)
            timeline = stats.get("timeline", [])
            if not timeline:
                timeline = _history_as_timeline(load_history(), selected_editor)
            display_time_series(console, timeline, group_by, selected_editor)
            save_history_entry(selected_editor, stats)

        elif plain == "Export Last Run":
            console.print("[yellow]No recent scan to export in this session. Run a scan first.[/yellow]")

        elif plain == "View History":
            display_history()

        elif plain == "Settings":
            cfg = settings_menu(cfg)
            detected = detect_editors(cfg)

        elif plain == "Exit":
            console.print("[dim]Goodbye![/dim]")
            break


if __name__ == "__main__":
    main()
