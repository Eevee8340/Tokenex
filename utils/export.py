import csv
import json
import os
from datetime import datetime
from pathlib import Path

EXPORT_DIR = Path.home() / ".tokenex" / "exports"


def export_json(editor_name: str, stats: dict) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tokenex_export_{editor_name.lower().replace(' ', '_')}_{timestamp}.json"
    filepath = EXPORT_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "editor": editor_name,
            "exported_at": datetime.now().isoformat(),
            "stats": stats
        }, f, indent=2, default=str)
    return filepath


def export_csv(editor_name: str, stats: dict) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tokenex_export_{editor_name.lower().replace(' ', '_')}_{timestamp}.csv"
    filepath = EXPORT_DIR / filename

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Editor", editor_name])
        writer.writerow(["Exported At", datetime.now().isoformat()])
        writer.writerow(["Total Processed Tokens", stats.get("total_processed", 0)])
        writer.writerow(["Input Tokens", stats.get("input", 0)])
        writer.writerow(["Output Tokens", stats.get("output", 0)])
        writer.writerow(["Cached Tokens", stats.get("cached", 0)])
        writer.writerow(["Thought Tokens", stats.get("thoughts", 0)])
        writer.writerow(["Total Turns", stats.get("total_turns", 0)])
        writer.writerow(["Total Sessions", stats.get("total_sessions", 0)])
        writer.writerow([])
        writer.writerow(["Model", "Input", "Output", "Total"])
        for model, m_stats in sorted(stats.get("models", {}).items(), key=lambda x: x[1].get("total", 0) if isinstance(x[1], dict) else x[1], reverse=True):
            if isinstance(m_stats, dict):
                writer.writerow([model, m_stats.get("input", 0), m_stats.get("output", 0), m_stats.get("total", 0)])
            else:
                writer.writerow([model, "—", "—", m_stats])
        writer.writerow([])
        writer.writerow(["Project", "Input", "Output", "Total"])
        for proj, p_stats in sorted(stats.get("projects", {}).items(), key=lambda x: x[1].get("total", 0), reverse=True):
            writer.writerow([proj, p_stats.get("input", 0), p_stats.get("output", 0), p_stats.get("total", 0)])
    return filepath
