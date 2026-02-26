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

    current_price = data.get("current_price") or data.get("currentPrice")
    percentiles = data.get("percentiles") or data.get("data") or {}

    table = Table(title="BTC 24h Prediction Percentiles")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Asset", "BTC")
    table.add_row("Horizon", "24h")

    if current_price is not None:
        table.add_row("Current Price", f"${current_price:,.2f}")

    if isinstance(percentiles, dict):
        table.add_row("Percentile Keys", ", ".join(str(k) for k in percentiles.keys()))
    elif isinstance(percentiles, list):
        table.add_row("Timepoints", str(len(percentiles)))

    # Show full response keys for debugging
    table.add_row("Response Keys", ", ".join(data.keys()))

    console.print(table)
    console.print("\n[green]API connection verified.[/green]\n")


if __name__ == "__main__":
    main()
