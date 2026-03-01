"""Edge resolution tracking — records detected edges and checks outcomes.

Turns "we found edges" into "we found edges that make money" by
tracking each edge from detection through resolution and computing
cumulative accuracy statistics.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.config import SUPABASE_KEY, SUPABASE_URL

logger = logging.getLogger("alphalog.edge_tracker")

# Directions that indicate a simple Up/Down bet
_UP_DIRECTIONS = {"UP", "SKEW_BULLISH", "UP_RISK"}
_DOWN_DIRECTIONS = {"DOWN", "SKEW_BEARISH", "DOWN_RISK", "AGAINST_UP"}
_AGAINST_DIRECTIONS = {"AGAINST_UP", "AGAINST_DOWN"}


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class EdgeTracker:
    """Records detected edges and tracks their resolution."""

    def __init__(self, data_dir: str = "data/edges") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._open_path = self._data_dir / "open_edges.json"
        self._resolved_path = self._data_dir / "resolved_edges.json"

    # ── Persistence helpers ──────────────────────────────────────────

    def _load_json(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _save_json(self, path: Path, data: list[dict]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    # ── Recording ────────────────────────────────────────────────────

    def record_edges(
        self,
        edges: list[dict],
        snapshot: dict,
    ) -> int:
        """Record new edges from EdgeDetector with resolution metadata.

        Args:
            edges: Output from EdgeDetector.detect_edges().
            snapshot: The full AlphaLog snapshot (for price/deadline data).

        Returns:
            Number of edges recorded.
        """
        if not edges:
            return 0

        snapshot_ts = snapshot.get("timestamp", _now_utc().isoformat())
        assets_data = snapshot.get("assets", {})
        open_edges = self._load_json(self._open_path)
        recorded = 0

        for edge in edges:
            asset = edge.get("asset", "")
            asset_data = assets_data.get(asset, {})
            timeframe = edge.get("timeframe", "daily")

            # Extract Polymarket data for deadline and prices
            pm_key = f"polymarket_{timeframe}"
            pm_data = asset_data.get(pm_key, {})

            deadline = self._resolve_deadline(timeframe, pm_data, snapshot_ts)
            if not deadline:
                continue

            # Determine the probabilities for PnL calculation
            synth_signal = edge.get("synth_signal", {})
            pm_price = edge.get("polymarket_price", {})
            synth_prob = synth_signal.get("synth_probability_up")
            pm_prob = pm_price.get("probability_up")

            # For edge direction, compute the probability of "our side"
            direction = edge.get("direction", "")
            our_pm_prob = self._our_side_probability(direction, pm_prob)

            edge_size = abs((synth_prob or 0) - (pm_prob or 0)) if synth_prob is not None and pm_prob is not None else None

            record = {
                "id": str(uuid4()),
                "detected_at": snapshot_ts,
                "asset": asset,
                "edge_type": edge.get("edge_type", ""),
                "timeframe": timeframe,
                "direction": direction,
                "confidence": edge.get("confidence", ""),
                "synth_probability": synth_prob,
                "polymarket_probability": pm_prob,
                "our_side_pm_probability": our_pm_prob,
                "edge_size": round(edge_size, 4) if edge_size is not None else None,
                "current_price": asset_data.get("current_price"),
                "start_price": pm_data.get("start_price"),
                "forecast_width": synth_signal.get("forecast_width"),
                "resolution_deadline": deadline,
                "resolved": False,
                "resolution": None,
                "actual_outcome": None,
                "pnl": None,
            }

            open_edges.append(record)
            recorded += 1

        self._save_json(self._open_path, open_edges)

        if recorded:
            self._save_supabase_batch(open_edges[-recorded:])
            logger.info("Recorded %d new edge(s)", recorded)

        return recorded

    def _resolve_deadline(
        self, timeframe: str, pm_data: dict, snapshot_ts: str
    ) -> str | None:
        """Determine when this edge's market resolves."""
        # Use event_end_time from Polymarket data if available
        event_end = pm_data.get("event_end_time")
        if event_end:
            return event_end

        # Fallback: estimate from timeframe
        ts = _parse_ts(snapshot_ts)
        if timeframe == "daily":
            # End of day at 17:00 ET (22:00 UTC)
            eod = ts.replace(hour=22, minute=0, second=0, microsecond=0)
            if ts.hour >= 22:
                eod += timedelta(days=1)
            return eod.isoformat()
        if timeframe == "hourly":
            return (ts + timedelta(hours=1)).isoformat()
        if timeframe == "15min":
            return (ts + timedelta(minutes=15)).isoformat()
        return None

    def _our_side_probability(self, direction: str, pm_prob_up: float | None) -> float | None:
        """Compute the Polymarket probability of the side we're betting on."""
        if pm_prob_up is None:
            return None
        if direction in _UP_DIRECTIONS:
            return pm_prob_up
        if direction in _DOWN_DIRECTIONS:
            return 1.0 - pm_prob_up
        if direction == "AGAINST_DOWN":
            return pm_prob_up  # We think Down is wrong, so we'd buy Up
        return pm_prob_up  # Default fallback

    # ── Resolution ───────────────────────────────────────────────────

    def resolve_edges(self, current_snapshot: dict) -> tuple[int, int]:
        """Check open edges against current data for resolution.

        Args:
            current_snapshot: The latest AlphaLog snapshot.

        Returns:
            (resolved_count, correct_count)
        """
        open_edges = self._load_json(self._open_path)
        if not open_edges:
            return 0, 0

        now = _now_utc()
        assets_data = current_snapshot.get("assets", {})

        still_open: list[dict] = []
        newly_resolved: list[dict] = []

        for edge in open_edges:
            deadline_str = edge.get("resolution_deadline")
            if not deadline_str:
                still_open.append(edge)
                continue

            deadline = _parse_ts(deadline_str)
            if now < deadline:
                still_open.append(edge)
                continue

            # Past deadline — resolve
            asset = edge.get("asset", "")
            asset_data = assets_data.get(asset, {})
            current_price = asset_data.get("current_price")
            start_price = edge.get("start_price") or edge.get("current_price")

            resolution = self._resolve_single(edge, current_price, start_price)
            edge.update(resolution)
            edge["resolved"] = True
            edge["resolved_at"] = now.isoformat()
            newly_resolved.append(edge)

        # Save
        self._save_json(self._open_path, still_open)

        resolved_edges = self._load_json(self._resolved_path)
        resolved_edges.extend(newly_resolved)
        self._save_json(self._resolved_path, resolved_edges)

        # Update Supabase
        for edge in newly_resolved:
            self._update_supabase_resolution(edge)

        correct = sum(1 for e in newly_resolved if e.get("resolution") == "CORRECT")
        if newly_resolved:
            logger.info(
                "Resolved %d edge(s): %d correct, %d incorrect",
                len(newly_resolved), correct, len(newly_resolved) - correct,
            )

        return len(newly_resolved), correct

    def _resolve_single(
        self,
        edge: dict,
        current_price: float | None,
        start_price: float | None,
    ) -> dict[str, Any]:
        """Determine if a single edge was correct."""
        direction = edge.get("direction", "")
        edge_type = edge.get("edge_type", "")
        our_pm_prob = edge.get("our_side_pm_probability")

        if current_price is None or start_price is None:
            return {
                "resolution": "UNKNOWN",
                "actual_outcome": "NO_DATA",
                "pnl": 0.0,
            }

        price_went_up = current_price > start_price
        actual_outcome = "UP" if price_went_up else "DOWN"

        # Determine correctness based on edge type
        if edge_type == "uncertainty_underpriced":
            correct = self._resolve_uncertainty(direction, price_went_up, edge)
        elif edge_type == "tail_risk_underpriced":
            correct = self._resolve_tail_risk(direction, current_price, start_price, edge)
        else:
            # probability_divergence, skew_mismatch — simple directional
            correct = self._resolve_directional(direction, price_went_up)

        resolution = "CORRECT" if correct else "INCORRECT"

        # PnL: assume $1 bet
        if our_pm_prob and our_pm_prob > 0:
            pnl = (1.0 / our_pm_prob) - 1.0 if correct else -1.0
        else:
            pnl = 1.0 if correct else -1.0

        return {
            "resolution": resolution,
            "actual_outcome": actual_outcome,
            "actual_price": current_price,
            "pnl": round(pnl, 4),
        }

    def _resolve_directional(self, direction: str, price_went_up: bool) -> bool:
        """Simple directional resolution: did price move in our predicted direction?"""
        if direction in _UP_DIRECTIONS:
            return price_went_up
        if direction in _DOWN_DIRECTIONS:
            return not price_went_up
        return False

    def _resolve_uncertainty(
        self, direction: str, price_went_up: bool, edge: dict
    ) -> bool:
        """Uncertainty underpriced: correct if the confident side was wrong."""
        # AGAINST_UP means we think Polymarket's confident Up is wrong
        if direction == "AGAINST_UP":
            return not price_went_up
        # AGAINST_DOWN means we think Polymarket's confident Down is wrong
        if direction == "AGAINST_DOWN":
            return price_went_up
        return False

    def _resolve_tail_risk(
        self,
        direction: str,
        current_price: float,
        start_price: float,
        edge: dict,
    ) -> bool:
        """Tail risk: correct if price moved significantly in the indicated direction."""
        # Parse forecast_width from the edge signal
        width_str = (edge.get("forecast_width") or
                     edge.get("synth_signal", {}).get("forecast_width", "0"))
        if isinstance(width_str, str):
            width_str = width_str.rstrip("%")
            try:
                width = float(width_str) / 100 if float(width_str) > 1 else float(width_str)
            except ValueError:
                width = 0.02
        else:
            width = float(width_str)

        move_pct = (current_price - start_price) / start_price

        # DOWN_RISK is correct if price dropped more than half the forecast width
        if direction == "DOWN_RISK":
            return move_pct < -(width / 2)
        # UP_RISK is correct if price rose more than half the forecast width
        if direction == "UP_RISK":
            return move_pct > (width / 2)
        return False

    # ── Statistics ───────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Compute cumulative performance statistics."""
        resolved = self._load_json(self._resolved_path)
        open_edges = self._load_json(self._open_path)

        total_resolved = len(resolved)
        total_open = len(open_edges)

        if total_resolved == 0:
            return {
                "total_edges_detected": total_resolved + total_open,
                "total_resolved": 0,
                "total_open": total_open,
                "correct": 0,
                "incorrect": 0,
                "hit_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl_per_edge": 0.0,
                "sharpe_ratio": 0.0,
                "by_asset": {},
                "by_edge_type": {},
                "by_confidence": {},
            }

        correct = sum(1 for e in resolved if e.get("resolution") == "CORRECT")
        incorrect = total_resolved - correct
        pnls = [e.get("pnl", 0.0) for e in resolved]
        total_pnl = sum(pnls)
        avg_pnl = total_pnl / total_resolved if total_resolved else 0.0

        # Sharpe: annualize assuming ~24 edges/day (hourly collection)
        if len(pnls) > 1:
            mean_pnl = avg_pnl
            std_pnl = (sum((p - mean_pnl) ** 2 for p in pnls) / (len(pnls) - 1)) ** 0.5
            sharpe = (mean_pnl / std_pnl * math.sqrt(365 * 24)) if std_pnl > 0 else 0.0
        else:
            sharpe = 0.0

        return {
            "total_edges_detected": total_resolved + total_open,
            "total_resolved": total_resolved,
            "total_open": total_open,
            "correct": correct,
            "incorrect": incorrect,
            "hit_rate": round(correct / total_resolved, 4) if total_resolved else 0.0,
            "total_pnl": round(total_pnl, 4),
            "avg_pnl_per_edge": round(avg_pnl, 4),
            "sharpe_ratio": round(sharpe, 4),
            "by_asset": self._group_stats(resolved, "asset"),
            "by_edge_type": self._group_stats(resolved, "edge_type"),
            "by_confidence": self._group_stats(resolved, "confidence"),
        }

    def _group_stats(self, resolved: list[dict], key: str) -> dict:
        """Compute per-group statistics."""
        groups: dict[str, list[dict]] = {}
        for e in resolved:
            group = e.get(key, "unknown")
            groups.setdefault(group, []).append(e)

        result: dict[str, dict] = {}
        for group, edges in sorted(groups.items()):
            total = len(edges)
            correct = sum(1 for e in edges if e.get("resolution") == "CORRECT")
            pnls = [e.get("pnl", 0.0) for e in edges]
            result[group] = {
                "total": total,
                "correct": correct,
                "incorrect": total - correct,
                "hit_rate": round(correct / total, 4) if total else 0.0,
                "total_pnl": round(sum(pnls), 4),
                "avg_pnl": round(sum(pnls) / total, 4) if total else 0.0,
            }

        return result

    # ── Open/resolved accessors ──────────────────────────────────────

    def get_open_edges(self) -> list[dict]:
        return self._load_json(self._open_path)

    def get_resolved_edges(self, limit: int = 50) -> list[dict]:
        resolved = self._load_json(self._resolved_path)
        return resolved[-limit:]

    # ── Supabase ─────────────────────────────────────────────────────

    def _save_supabase_batch(self, edges: list[dict]) -> None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            rows = [
                {
                    "id": e["id"],
                    "detected_at": e["detected_at"],
                    "asset": e["asset"],
                    "edge_type": e["edge_type"],
                    "direction": e["direction"],
                    "confidence": e["confidence"],
                    "synth_probability": e.get("synth_probability"),
                    "polymarket_probability": e.get("polymarket_probability"),
                    "edge_size": e.get("edge_size"),
                    "current_price": e.get("current_price"),
                    "resolution_deadline": e.get("resolution_deadline"),
                    "resolved": False,
                }
                for e in edges
            ]
            client.table("edge_tracking").insert(rows).execute()
        except Exception as exc:
            logger.warning("Supabase edge save failed (non-fatal): %s", exc)

    def _update_supabase_resolution(self, edge: dict) -> None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            client.table("edge_tracking").update({
                "resolved": True,
                "resolution": edge.get("resolution"),
                "actual_outcome": edge.get("actual_outcome"),
                "pnl": edge.get("pnl"),
                "resolved_at": edge.get("resolved_at"),
            }).eq("id", edge["id"]).execute()
        except Exception as exc:
            logger.warning("Supabase edge update failed (non-fatal): %s", exc)
