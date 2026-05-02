import json
from datetime import datetime
from pathlib import Path

HISTORY_FILE = Path.home() / ".tokenex" / "history.json"


def load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_history_entry(editor_name: str, stats: dict):
    history = load_history()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "editor": editor_name,
        "total_processed": stats.get("total_processed", 0),
        "input": stats.get("input", 0),
        "output": stats.get("output", 0),
        "cached": stats.get("cached", 0),
        "thoughts": stats.get("thoughts", 0),
        "total_turns": stats.get("total_turns", 0),
        "total_sessions": stats.get("total_sessions", 0),
        "projects": stats.get("projects", {}),
        "models": stats.get("models", {}),
    }
    history.append(entry)
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-50:], f, indent=2)


def get_last_entry(editor_name: str) -> dict | None:
    history = load_history()
    for entry in reversed(history):
        if entry.get("editor") == editor_name:
            return entry
    return None


def _parse_ts(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(ts).replace(tzinfo=None)
    except ValueError:
        return datetime.min


def _relative_time(dt: datetime) -> str:
    from datetime import timedelta
    now = datetime.now()
    diff = now - dt
    if diff < timedelta(seconds=10):
        return "just now"
    if diff < timedelta(minutes=1):
        return f"{int(diff.total_seconds())}s ago"
    if diff < timedelta(hours=1):
        return f"{int(diff.total_seconds() // 60)}m ago"
    if diff < timedelta(days=1):
        return f"{int(diff.total_seconds() // 3600)}h ago"
    yesterday = now - timedelta(days=1)
    if dt.year == yesterday.year and dt.month == yesterday.month and dt.day == yesterday.day:
        return f"Yesterday {dt.strftime('%H:%M')}"
    if dt.year == now.year:
        return dt.strftime("%b %d %H:%M")
    return dt.strftime("%b %d, %Y %H:%M")


def _fmt_delta(curr: int, prev: int | None) -> str:
    if prev is None:
        return "[dim]—[/dim]"
    delta = curr - prev
    if delta > 0:
        return f"[green]+{delta:,}[/green]"
    if delta < 0:
        return f"[red]−{abs(delta):,}[/red]"
    return "[dim]0[/dim]"


def display_history():
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from collections import defaultdict
    from .charts import sparkline

    console = Console()
    history = load_history()
    if not history:
        console.print("[yellow]No history entries found yet.[/yellow]")
        return

    # Group by editor
    by_editor = defaultdict(list)
    for entry in history:
        by_editor[entry.get("editor", "?")].append(entry)

    # Summary
    total_scans = len(history)
    most_recent = max(history, key=lambda e: e.get("timestamp", ""))
    editors_with_data = list(by_editor.keys())
    summary_text = (
        f"[bold]{total_scans}[/bold] total scans  •  "
        f"most recent: [cyan]{_relative_time(_parse_ts(most_recent.get('timestamp', '')))}[/cyan]  •  "
        f"editors: [yellow]{', '.join(editors_with_data)}[/yellow]"
    )
    console.print(Panel(summary_text, title="[bold]History Summary[/bold]", border_style="blue"))

    for editor_name in sorted(editors_with_data):
        entries = by_editor[editor_name]
        # Take last 10 (most recent), reverse to newest-first
        recent = entries[-10:][::-1]

        table = Table(
            title=f"[bold]{editor_name}[/bold]  ({len(entries)} total, showing last {len(recent)})",
            show_header=True,
            header_style="bold magenta",
            title_style="bold cyan"
        )
        table.add_column("When", style="dim")
        table.add_column("Total", justify="right")
        table.add_column("Δ Total", justify="right")
        table.add_column("Input", justify="right")
        table.add_column("Δ Input", justify="right")
        table.add_column("Output", justify="right")
        table.add_column("Δ Output", justify="right")
        table.add_column("Sessions", justify="right")
        table.add_column("Δ Sess", justify="right")

        totals = []
        inputs = []
        outputs = []
        for i, entry in enumerate(recent):
            ts_str = entry.get("timestamp", "")
            dt = _parse_ts(ts_str)
            when = _relative_time(dt)

            total = entry.get("total_processed", 0)
            inp = entry.get("input", 0)
            out = entry.get("output", 0)
            sess = entry.get("total_sessions", 0)

            totals.append(total)
            inputs.append(inp)
            outputs.append(out)

            next_total = recent[i + 1].get("total_processed") if i + 1 < len(recent) else None
            next_input = recent[i + 1].get("input") if i + 1 < len(recent) else None
            next_output = recent[i + 1].get("output") if i + 1 < len(recent) else None
            next_sess = recent[i + 1].get("total_sessions") if i + 1 < len(recent) else None

            d_total = _fmt_delta(total, next_total)
            d_input = _fmt_delta(inp, next_input)
            d_output = _fmt_delta(out, next_output)
            d_sess = _fmt_delta(sess, next_sess)

            table.add_row(
                when,
                f"{total:,}",
                d_total,
                f"{inp:,}",
                d_input,
                f"{out:,}",
                d_output,
                f"{sess:,}",
                d_sess,
            )

        console.print(table)

        # Sparklines
        spark_total = sparkline([float(v) for v in totals])
        spark_input = sparkline([float(v) for v in inputs])
        spark_output = sparkline([float(v) for v in outputs])
        spark_text = (
            f"[dim]Trends (newest → oldest):  "
            f"Total [cyan]{spark_total}[/cyan]  |  "
            f"Input [green]{spark_input}[/green]  |  "
            f"Output [magenta]{spark_output}[/magenta][/dim]"
        )
        console.print(spark_text)
        console.print()
