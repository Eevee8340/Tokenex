"""Terminal charting utilities for Tokenex using Rich."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel


SPARK_TICKS = " ▁▂▃▄▅▆▇█"


def sparkline(values: List[float]) -> str:
    """Return a unicode sparkline string from a list of numbers."""
    if not values:
        return ""
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return " " * len(values)
    span = max_val - min_val
    chars = []
    for v in values:
        idx = int((v - min_val) / span * (len(SPARK_TICKS) - 1))
        chars.append(SPARK_TICKS[idx])
    return "".join(chars)


def display_top_n_current(console: Console, stats: dict, n: int = 5):
    """Show a Rich bar chart of the top-N projects from a single scan."""
    projects = stats.get("projects")
    if not projects:
        console.print("[yellow]No project data available for Top-N ranking.[/yellow]")
        return

    ranked = sorted(
        projects.items(),
        key=lambda x: x[1].get("total", 0) if isinstance(x[1], dict) else x[1],
        reverse=True,
    )[:n]

    max_total = max(
        (x[1].get("total", 0) if isinstance(x[1], dict) else x[1]) for x in ranked
    ) if ranked else 0

    table = Table(
        title=f"[bold]Top {len(ranked)} Projects by Tokens[/bold]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Rank", justify="right", style="dim")
    table.add_column("Project")
    table.add_column("Tokens", justify="right")
    table.add_column("Bar")

    for i, (proj, p_stats) in enumerate(ranked, start=1):
        total = p_stats.get("total", 0) if isinstance(p_stats, dict) else p_stats
        bar_len = int((total / max_total) * 40) if max_total else 0
        bar = "█" * bar_len
        table.add_row(str(i), proj, f"{total:,}", f"[cyan]{bar}[/cyan]")

    console.print(table)


def display_top_n_history(console: Console, history: List[dict], editor_name: str, n: int = 5):
    """Aggregate projects across all history entries for an editor and show top-N."""
    agg = defaultdict(lambda: {"total": 0, "input": 0, "output": 0})
    for entry in history:
        if entry.get("editor") != editor_name:
            continue
        projects = entry.get("projects", {})
        for proj, p_stats in projects.items():
            if isinstance(p_stats, dict):
                agg[proj]["total"] += p_stats.get("total", 0)
                agg[proj]["input"] += p_stats.get("input", 0)
                agg[proj]["output"] += p_stats.get("output", 0)
            else:
                agg[proj]["total"] += p_stats

    if not agg:
        console.print(f"[yellow]No historical project data for {editor_name}.[/yellow]")
        return

    ranked = sorted(agg.items(), key=lambda x: x[1]["total"], reverse=True)[:n]
    max_total = max(x[1]["total"] for x in ranked) if ranked else 0

    table = Table(
        title=f"[bold]Historical Top {len(ranked)} Projects ({editor_name})[/bold]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Rank", justify="right", style="dim")
    table.add_column("Project")
    table.add_column("Total", justify="right")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Bar")

    for i, (proj, p_stats) in enumerate(ranked, start=1):
        total = p_stats["total"]
        bar_len = int((total / max_total) * 40) if max_total else 0
        bar = "█" * bar_len
        table.add_row(
            str(i),
            proj,
            f"{total:,}",
            f"{p_stats['input']:,}",
            f"{p_stats['output']:,}",
            f"[cyan]{bar}[/cyan]",
        )

    console.print(table)


def _group_timeline(timeline: List[dict], group_by: str) -> Dict[str, int]:
    """Group a list of {"date": datetime, "tokens": int} by Day/Week/Month."""
    buckets = defaultdict(int)
    for event in timeline:
        dt = event.get("date")
        if not isinstance(dt, datetime):
            continue
        tokens = event.get("tokens", 0)
        if group_by == "Day":
            key = dt.strftime("%Y-%m-%d")
        elif group_by == "Week":
            key = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
        elif group_by == "Month":
            key = dt.strftime("%Y-%m")
        else:
            key = dt.strftime("%Y-%m-%d")
        buckets[key] += tokens
    return dict(buckets)


def _history_as_timeline(history: List[dict], editor_name: str) -> List[dict]:
    """Convert history scan timestamps into a fallback timeline."""
    timeline = []
    for entry in history:
        if entry.get("editor") != editor_name:
            continue
        ts = entry.get("timestamp")
        try:
            dt = datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            continue
        timeline.append({"date": dt, "tokens": entry.get("total_processed", 0)})
    return timeline


def display_time_series(console: Console, timeline: List[dict], group_by: str, title: str):
    """Render a terminal bar chart from a timeline using Rich text bars."""
    if not timeline:
        console.print("[yellow]No time-series data available.[/yellow]")
        return

    buckets = _group_timeline(timeline, group_by)
    if not buckets:
        console.print("[yellow]No time-series data after grouping.[/yellow]")
        return

    sorted_keys = sorted(buckets.keys())
    values = [buckets[k] for k in sorted_keys]

    max_val = max(values) if values else 0
    table = Table(
        title=f"[bold]{title} — {group_by}[/bold]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Period")
    table.add_column("Tokens", justify="right")
    table.add_column("Bar")

    for i, (k, v) in enumerate(zip(sorted_keys, values)):
        bar_len = int((v / max_val) * 40) if max_val else 0
        bar = "█" * bar_len
        table.add_row(k, f"{v:,}", f"[cyan]{bar}[/cyan]")
        if i < len(sorted_keys) - 1:
            table.add_row("", "", "")

    console.print(table)

