from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

console = Console()


def display_editor_stats(name: str, stats: dict):
    console.print(f"\n[bold cyan]{name} Token Usage Summary[/bold cyan]")

    main_table = Table(show_header=True, header_style="bold magenta")
    main_table.add_column("Metric", style="dim")
    main_table.add_column("Value", justify="right")

    main_table.add_row("Total Processed Tokens", f"{stats.get('total_processed', 0):,}")
    main_table.add_row("Input Tokens", f"{stats.get('input', 0):,}")
    main_table.add_row("Output Tokens", f"{stats.get('output', 0):,}")
    main_table.add_row("Cached Tokens", f"{stats.get('cached', 0):,}")
    main_table.add_row("Thought Tokens", f"{stats.get('thoughts', 0):,}")
    main_table.add_row("Total Turns", f"{stats.get('total_turns', 0):,}")
    main_table.add_row("Total Sessions", f"{stats.get('total_sessions', 0):,}")

    console.print(main_table)

    models = stats.get('models')
    if models:
        model_table = Table(title="Usage by Model", show_header=True, header_style="bold green")
        model_table.add_column("Model")
        model_table.add_column("Input", justify="right")
        model_table.add_column("Output", justify="right")
        model_table.add_column("Total", justify="right")
        for model, m_stats in sorted(models.items(), key=lambda x: x[1].get('total', 0) if isinstance(x[1], dict) else x[1], reverse=True):
            if isinstance(m_stats, dict):
                model_table.add_row(
                    model,
                    f"{m_stats.get('input', 0):,}",
                    f"{m_stats.get('output', 0):,}",
                    f"{m_stats.get('total', 0):,}"
                )
            else:
                model_table.add_row(model, "—", "—", f"{m_stats:,}")
        console.print(model_table)

    projects = stats.get('projects')
    if projects:
        proj_table = Table(title="Usage by Project/Workspace", show_header=True, header_style="bold blue")
        proj_table.add_column("Workspace")
        proj_table.add_column("Input", justify="right")
        proj_table.add_column("Output", justify="right")
        proj_table.add_column("Total", justify="right")
        for proj, p_stats in sorted(projects.items(), key=lambda x: x[1].get('total', 0), reverse=True):
            proj_table.add_row(
                proj,
                f"{p_stats.get('input', 0):,}",
                f"{p_stats.get('output', 0):,}",
                f"{p_stats.get('total', 0):,}"
            )
        console.print(proj_table)


def display_comparison(all_stats: dict):
    console.print("\n[bold cyan]All Editors — Comparison[/bold cyan]")

    comp_table = Table(show_header=True, header_style="bold magenta")
    comp_table.add_column("Editor", style="dim")
    comp_table.add_column("Input", justify="right")
    comp_table.add_column("Output", justify="right")
    comp_table.add_column("Total", justify="right")
    comp_table.add_column("Sessions", justify="right")
    comp_table.add_column("Turns", justify="right")

    grand_input = grand_output = grand_total = grand_sessions = grand_turns = 0

    for editor_name, stats in sorted(all_stats.items(), key=lambda x: x[1].get('total_processed', 0), reverse=True):
        inp = stats.get('input', 0)
        out = stats.get('output', 0)
        tot = stats.get('total_processed', 0)
        sess = stats.get('total_sessions', 0)
        turns = stats.get('total_turns', 0)
        comp_table.add_row(editor_name, f"{inp:,}", f"{out:,}", f"{tot:,}", f"{sess:,}", f"{turns:,}")
        grand_input += inp
        grand_output += out
        grand_total += tot
        grand_sessions += sess
        grand_turns += turns

    comp_table.add_row("[bold]Grand Total[/bold]", f"[bold]{grand_input:,}[/bold]", f"[bold]{grand_output:,}[/bold]", f"[bold]{grand_total:,}[/bold]", f"[bold]{grand_sessions:,}[/bold]", f"[bold]{grand_turns:,}[/bold]")
    console.print(comp_table)
