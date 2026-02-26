"""Quick verification that the Synth API is accessible and returning data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table

from backend.synth_client import SynthClient, SynthAPIError

console = Console()


def main() -> None:
    client = SynthClient()

    console.print("\n[bold]Forked — Synth API Verification[/bold]\n")

    try:
        data = client.get_prediction_percentiles("BTC", "24h")
    except SynthAPIError as e:
        console.print(f"[red]API Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Connection Error: {e}[/red]")
        sys.exit(1)

    current_price = data.get("current_price")
    forecast_future = data.get("forecast_future", {})
    percentiles = forecast_future.get("percentiles", [])

    table = Table(title="BTC 24h Prediction Percentiles")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Asset", "BTC")
    table.add_row("Horizon", "24h")

    if current_price is not None:
        table.add_row("Current Price", f"${current_price:,.2f}")

    table.add_row("Forecast Timepoints", str(len(percentiles)))

    if percentiles:
        first = percentiles[0]
        last = percentiles[-1]
        levels = sorted(first.keys())
        table.add_row("Percentile Levels", ", ".join(levels))

        p50_start = first.get("0.5")
        p50_end = last.get("0.5")
        if p50_start is not None:
            table.add_row("Median (start)", f"${p50_start:,.2f}")
        if p50_end is not None:
            table.add_row("Median (end)", f"${p50_end:,.2f}")

    console.print(table)
    console.print("\n[green]API connection verified.[/green]\n")


if __name__ == "__main__":
    main()
