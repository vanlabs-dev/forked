"""CLI runner for Synth-Index analysis.

Usage:
    python -m backend.analysis.runner --latest     Analyze most recent snapshot
    python -m backend.analysis.runner --compare    Compare latest two snapshots
    python -m backend.analysis.runner --all        Analyze all local snapshots
    python -m backend.analysis.runner --edges      Show open edges and recent resolutions
    python -m backend.analysis.runner --stats      Show cumulative edge performance
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
from backend.analysis.edge_tracker import EdgeTracker

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


def cmd_edges() -> None:
    """Show current open edges and recent resolutions."""
    tracker = EdgeTracker()

    open_edges = tracker.get_open_edges()
    if open_edges:
        table = Table(title=f"Open Edges ({len(open_edges)})", show_lines=True)
        table.add_column("Asset", style="bold cyan", width=8)
        table.add_column("Type", width=22)
        table.add_column("TF", width=8)
        table.add_column("Dir", width=14)
        table.add_column("Conf", width=8)
        table.add_column("Edge", justify="right", width=8)
        table.add_column("Deadline", width=22)
        table.add_column("Detected", width=22)

        conf_colors = {"HIGH": "bold red", "MEDIUM": "yellow", "LOW": "dim"}

        for e in open_edges:
            color = conf_colors.get(e.get("confidence", ""), "white")
            edge_size = e.get("edge_size")
            edge_str = f"{edge_size:.1%}" if edge_size is not None else "-"
            deadline = e.get("resolution_deadline", "")
            if isinstance(deadline, str) and len(deadline) > 19:
                deadline = deadline[:19]
            detected = e.get("detected_at", "")
            if isinstance(detected, str) and len(detected) > 19:
                detected = detected[:19]

            table.add_row(
                e.get("asset", ""),
                e.get("edge_type", ""),
                e.get("timeframe", ""),
                e.get("direction", ""),
                f"[{color}]{e.get('confidence', '')}[/]",
                edge_str,
                deadline,
                detected,
            )
        console.print(table)
    else:
        console.print("[dim]No open edges.[/]")

    resolved = tracker.get_resolved_edges(limit=20)
    if resolved:
        console.print()
        table = Table(title=f"Recent Resolutions (last {len(resolved)})", show_lines=True)
        table.add_column("Asset", style="bold cyan", width=8)
        table.add_column("Type", width=22)
        table.add_column("Dir", width=14)
        table.add_column("Result", width=12)
        table.add_column("PnL", justify="right", width=10)
        table.add_column("Outcome", width=8)
        table.add_column("Resolved At", width=22)

        for e in reversed(resolved):
            resolution = e.get("resolution", "")
            if resolution == "CORRECT":
                res_str = "[bold green]CORRECT[/]"
            elif resolution == "INCORRECT":
                res_str = "[bold red]INCORRECT[/]"
            else:
                res_str = f"[dim]{resolution}[/]"

            pnl = e.get("pnl")
            if pnl is not None:
                pnl_str = f"[green]+${pnl:.2f}[/]" if pnl > 0 else f"[red]-${abs(pnl):.2f}[/]"
            else:
                pnl_str = "-"

            resolved_at = e.get("resolved_at", "")
            if isinstance(resolved_at, str) and len(resolved_at) > 19:
                resolved_at = resolved_at[:19]

            table.add_row(
                e.get("asset", ""),
                e.get("edge_type", ""),
                e.get("direction", ""),
                res_str,
                pnl_str,
                e.get("actual_outcome", ""),
                resolved_at,
            )
        console.print(table)
    else:
        console.print("\n[dim]No resolved edges yet.[/]")


def cmd_stats() -> None:
    """Show cumulative edge performance statistics."""
    tracker = EdgeTracker()
    stats = tracker.get_stats()

    # Summary panel
    hit_rate = stats["hit_rate"]
    hr_color = "green" if hit_rate > 0.55 else "yellow" if hit_rate > 0.45 else "red"
    pnl = stats["total_pnl"]
    pnl_color = "green" if pnl > 0 else "red" if pnl < 0 else "white"

    summary = (
        f"Detected: {stats['total_edges_detected']}  |  "
        f"Resolved: {stats['total_resolved']}  |  "
        f"Open: {stats['total_open']}  |  "
        f"Hit Rate: [{hr_color}]{hit_rate:.1%}[/]  |  "
        f"PnL: [{pnl_color}]${pnl:+.2f}[/]  |  "
        f"Sharpe: {stats['sharpe_ratio']:.2f}"
    )
    console.print(Panel(summary, title="Edge Performance Summary"))

    if not stats["total_resolved"]:
        console.print("\n[dim]No resolved edges yet. Stats will populate as edges resolve.[/]")
        return

    # By asset
    if stats["by_asset"]:
        table = Table(title="Performance by Asset", show_lines=True)
        table.add_column("Asset", style="bold cyan", width=10)
        table.add_column("Total", justify="right", width=8)
        table.add_column("Correct", justify="right", width=8)
        table.add_column("Hit Rate", justify="right", width=10)
        table.add_column("PnL", justify="right", width=10)
        table.add_column("Avg PnL", justify="right", width=10)

        for asset, s in sorted(stats["by_asset"].items()):
            hr = s["hit_rate"]
            hr_c = "green" if hr > 0.55 else "yellow" if hr > 0.45 else "red"
            p = s["total_pnl"]
            p_c = "green" if p > 0 else "red" if p < 0 else "white"
            table.add_row(
                asset,
                str(s["total"]),
                str(s["correct"]),
                f"[{hr_c}]{hr:.1%}[/]",
                f"[{p_c}]${p:+.2f}[/]",
                f"${s['avg_pnl']:+.2f}",
            )
        console.print()
        console.print(table)

    # By edge type
    if stats["by_edge_type"]:
        table = Table(title="Performance by Edge Type", show_lines=True)
        table.add_column("Edge Type", style="bold cyan", width=24)
        table.add_column("Total", justify="right", width=8)
        table.add_column("Correct", justify="right", width=8)
        table.add_column("Hit Rate", justify="right", width=10)
        table.add_column("PnL", justify="right", width=10)

        for etype, s in sorted(stats["by_edge_type"].items()):
            hr = s["hit_rate"]
            hr_c = "green" if hr > 0.55 else "yellow" if hr > 0.45 else "red"
            p = s["total_pnl"]
            p_c = "green" if p > 0 else "red" if p < 0 else "white"
            table.add_row(
                etype,
                str(s["total"]),
                str(s["correct"]),
                f"[{hr_c}]{hr:.1%}[/]",
                f"[{p_c}]${p:+.2f}[/]",
            )
        console.print()
        console.print(table)

    # By confidence
    if stats["by_confidence"]:
        table = Table(title="Performance by Confidence", show_lines=True)
        table.add_column("Confidence", style="bold cyan", width=12)
        table.add_column("Total", justify="right", width=8)
        table.add_column("Correct", justify="right", width=8)
        table.add_column("Hit Rate", justify="right", width=10)
        table.add_column("PnL", justify="right", width=10)

        for conf, s in sorted(stats["by_confidence"].items()):
            hr = s["hit_rate"]
            hr_c = "green" if hr > 0.55 else "yellow" if hr > 0.45 else "red"
            p = s["total_pnl"]
            p_c = "green" if p > 0 else "red" if p < 0 else "white"
            table.add_row(
                conf,
                str(s["total"]),
                str(s["correct"]),
                f"[{hr_c}]{hr:.1%}[/]",
                f"[{p_c}]${p:+.2f}[/]",
            )
        console.print()
        console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synth-Index analysis runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--latest", action="store_true", help="Analyze most recent snapshot")
    group.add_argument("--compare", action="store_true", help="Compare latest two snapshots")
    group.add_argument("--all", action="store_true", help="Analyze all local snapshots")
    group.add_argument("--edges", action="store_true", help="Show open edges and recent resolutions")
    group.add_argument("--stats", action="store_true", help="Show cumulative edge performance")

    args = parser.parse_args()

    if args.latest:
        cmd_latest()
    elif args.compare:
        cmd_compare()
    elif args.all:
        cmd_all()
    elif args.edges:
        cmd_edges()
    elif args.stats:
        cmd_stats()


if __name__ == "__main__":
    main()
