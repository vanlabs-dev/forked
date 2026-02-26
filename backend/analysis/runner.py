"""CLI runner for Synth-Index analysis.

Usage:
    python -m backend.analysis.runner --latest     Analyze most recent snapshot
    python -m backend.analysis.runner --compare    Compare latest two snapshots
    python -m backend.analysis.runner --all        Analyze all local snapshots
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from backend.analysis.distribution import DistributionAnalyzer
from backend.analysis.synth_index import SynthIndex
from backend.analysis.edge_detector import EdgeDetector
from backend.analysis.anomaly_detector import AnomalyDetector

SNAPSHOTS_DIR = Path("data/snapshots")

console = Console()


def find_snapshots() -> list[Path]:
    """Find all snapshot JSON files, sorted oldest to newest."""
    if not SNAPSHOTS_DIR.exists():
        return []
    snapshots = sorted(SNAPSHOTS_DIR.glob("*/*_snapshot.json"))
    return snapshots


def load_snapshot(path: Path) -> dict:
    """Load a snapshot from disk."""
    with open(path) as f:
        return json.load(f)


def render_distribution_table(metrics: dict) -> Table:
    """Build a rich table of distribution metrics."""
    table = Table(title="Distribution Metrics", show_lines=True)
    table.add_column("Asset", style="bold cyan", width=12)
    table.add_column("Horizon", width=8)
    table.add_column("Bias", justify="right", width=10)
    table.add_column("Width", justify="right", width=10)
    table.add_column("Skew", justify="right", width=8)
    table.add_column("Tail Fat", justify="right", width=9)
    table.add_column("Up Tail", justify="right", width=9)
    table.add_column("Dn Tail", justify="right", width=9)
    table.add_column("Density", justify="right", width=9)
    table.add_column("Regime", width=12)

    for key in sorted(metrics.keys()):
        m = metrics[key]
        bias = m["directional_bias"]
        bias_str = f"[green]+{bias:.4%}[/]" if bias > 0 else f"[red]{bias:.4%}[/]"

        regime = m["regime"]
        if regime == "STRESSED":
            regime_str = f"[bold red]{regime}[/]"
        elif regime == "COMPRESSED":
            regime_str = f"[bold yellow]{regime}[/]"
        else:
            regime_str = f"[green]{regime}[/]"

        table.add_row(
            m["asset"],
            m["horizon"],
            bias_str,
            f"{m['forecast_width']:.4%}",
            f"{m['tail_asymmetry']:.2f}",
            f"{m['tail_fatness']:.2f}",
            f"{m['upper_tail_risk']:.2f}",
            f"{m['lower_tail_risk']:.2f}",
            f"{m['density_concentration']:.2f}",
            regime_str,
        )

    return table


def render_index_table(index_data: dict) -> Table:
    """Build a rich table of Synth-Index scores."""
    table = Table(title="Synth-Index Scores", show_lines=True)
    table.add_column("Asset", style="bold cyan", width=12)
    table.add_column("Horizon", width=8)
    table.add_column("Score", justify="right", width=8)
    table.add_column("Level", width=16)
    table.add_column("Width", justify="right", width=8)
    table.add_column("Tail", justify="right", width=8)
    table.add_column("Skew", justify="right", width=8)
    table.add_column("Conc.", justify="right", width=8)

    level_colors = {
        "EXTREME": "bold red",
        "ELEVATED": "red",
        "ABOVE_AVERAGE": "yellow",
        "BELOW_AVERAGE": "green",
        "CALM": "bold green",
    }

    for key in sorted(index_data.keys()):
        d = index_data[key]
        level = d["level"]
        color = level_colors.get(level, "white")
        c = d["components"]

        table.add_row(
            d["asset"],
            d["horizon"],
            f"[{color}]{d['synth_index']:.1f}[/]",
            f"[{color}]{level}[/]",
            f"{c['width_contribution']:.1f}",
            f"{c['tail_contribution']:.1f}",
            f"{c['skew_contribution']:.1f}",
            f"{c['concentration_contribution']:.1f}",
        )

    return table


def render_edges(edges: list[dict]) -> None:
    """Print detected edges."""
    if not edges:
        console.print("\n[dim]No edges detected.[/]")
        return

    table = Table(title="Detected Edges", show_lines=True)
    table.add_column("Asset", style="bold cyan", width=8)
    table.add_column("Type", width=24)
    table.add_column("TF", width=8)
    table.add_column("Dir", width=16)
    table.add_column("Conf", width=8)
    table.add_column("Description", width=60)

    conf_colors = {"HIGH": "bold red", "MEDIUM": "yellow", "LOW": "dim"}

    for e in edges:
        color = conf_colors.get(e["confidence"], "white")
        table.add_row(
            e["asset"],
            e["edge_type"],
            e.get("timeframe", ""),
            e["direction"],
            f"[{color}]{e['confidence']}[/]",
            e["description"],
        )

    console.print()
    console.print(table)


def render_anomalies(anomalies: list[dict]) -> None:
    """Print detected anomalies."""
    if not anomalies:
        console.print("\n[dim]No anomalies detected.[/]")
        return

    table = Table(title="Anomalies (vs Previous Snapshot)", show_lines=True)
    table.add_column("Asset", style="bold cyan", width=8)
    table.add_column("Type", width=24)
    table.add_column("Severity", width=10)
    table.add_column("Previous", justify="right", width=12)
    table.add_column("Current", justify="right", width=12)
    table.add_column("Description", width=50)

    sev_colors = {"HIGH": "bold red", "MEDIUM": "yellow", "LOW": "dim"}

    for a in anomalies:
        color = sev_colors.get(a["severity"], "white")
        prev_val = a["previous_value"]
        curr_val = a["current_value"]

        # Format numeric values
        if isinstance(prev_val, float):
            prev_str = f"{prev_val:.4f}"
            curr_str = f"{curr_val:.4f}"
        else:
            prev_str = str(prev_val)
            curr_str = str(curr_val)

        table.add_row(
            a["asset"],
            a["anomaly_type"],
            f"[{color}]{a['severity']}[/]",
            prev_str,
            curr_str,
            a["description"],
        )

    console.print()
    console.print(table)


def analyze_single(snapshot_path: Path, show_header: bool = True) -> tuple[dict, dict]:
    """Analyze a single snapshot and display results.

    Returns (distribution_metrics, index_data) for further use.
    """
    snapshot = load_snapshot(snapshot_path)

    if show_header:
        ts = snapshot.get("timestamp", "unknown")
        partial = snapshot.get("partial", False)
        status = "[yellow]PARTIAL[/]" if partial else "[green]COMPLETE[/]"
        console.print(Panel(f"Snapshot: {snapshot_path.name}  |  {ts}  |  {status}"))

    analyzer = DistributionAnalyzer()
    metrics = analyzer.analyze_snapshot(snapshot)

    index = SynthIndex()
    index_data = index.compute(metrics)

    detector = EdgeDetector()
    edges = detector.detect_edges(snapshot, metrics)

    console.print(render_distribution_table(metrics))
    console.print()
    console.print(render_index_table(index_data))
    render_edges(edges)

    return metrics, index_data


def cmd_latest() -> None:
    """Analyze the most recent snapshot."""
    snapshots = find_snapshots()
    if not snapshots:
        console.print("[red]No snapshots found in data/snapshots/[/]")
        sys.exit(1)

    latest = snapshots[-1]
    analyze_single(latest)


def cmd_compare() -> None:
    """Compare the latest two snapshots."""
    snapshots = find_snapshots()
    if len(snapshots) < 2:
        console.print("[red]Need at least 2 snapshots for comparison.[/]")
        if snapshots:
            console.print("Running analysis on the only available snapshot instead.\n")
            analyze_single(snapshots[0])
        sys.exit(1)

    prev_path = snapshots[-2]
    curr_path = snapshots[-1]

    console.print(Panel("[bold]Previous Snapshot[/]"))
    prev_metrics, _ = analyze_single(prev_path, show_header=True)

    console.print("\n")
    console.print(Panel("[bold]Current Snapshot[/]"))
    curr_metrics, _ = analyze_single(curr_path, show_header=True)

    # Anomaly detection
    detector = AnomalyDetector()
    anomalies = detector.detect_anomalies(curr_metrics, prev_metrics)
    render_anomalies(anomalies)


def cmd_all() -> None:
    """Analyze all snapshots and show trends."""
    snapshots = find_snapshots()
    if not snapshots:
        console.print("[red]No snapshots found.[/]")
        sys.exit(1)

    console.print(f"[bold]Found {len(snapshots)} snapshot(s)[/]\n")

    prev_metrics: dict | None = None
    all_anomalies: list[dict] = []
    detector = AnomalyDetector()

    for i, path in enumerate(snapshots):
        console.print(f"\n{'=' * 80}")
        curr_metrics, _ = analyze_single(path)

        if prev_metrics:
            anomalies = detector.detect_anomalies(curr_metrics, prev_metrics)
            if anomalies:
                all_anomalies.extend(anomalies)
                render_anomalies(anomalies)

        prev_metrics = curr_metrics

    if len(snapshots) > 1:
        console.print(f"\n\n[bold]Total anomalies across all snapshots: {len(all_anomalies)}[/]")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synth-Index analysis runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--latest", action="store_true", help="Analyze most recent snapshot")
    group.add_argument("--compare", action="store_true", help="Compare latest two snapshots")
    group.add_argument("--all", action="store_true", help="Analyze all local snapshots")

    args = parser.parse_args()

    if args.latest:
        cmd_latest()
    elif args.compare:
        cmd_compare()
    elif args.all:
        cmd_all()


if __name__ == "__main__":
    main()
