export interface Asset {
  symbol: string;
  name: string;
  current_price: number | null;
  horizons: string[];
}

export interface ConePoint {
  seconds_ahead: number;
  hours_ahead: number;
  p005: number;
  p05: number;
  p20: number;
  p35: number;
  p50: number;
  p65: number;
  p80: number;
  p95: number;
  p995: number;
}

export interface ConeResponse {
  asset: string;
  current_price: number;
  horizon: string;
  points: ConePoint[];
}

export interface ProbabilityResponse {
  asset: string;
  target_price?: number;
  lower?: number;
  upper?: number;
  current_price: number;
  probability: number;
  probability_below_lower?: number;
  probability_above_upper?: number;
  horizon: string;
  timepoint_seconds: number;
  confidence: string;
  cone: ConeResponse;
}

export interface LiquidationInfo {
  price: number;
  probability: number;
  distance_pct: number;
  risk_level: string;
}

export interface TPSLInfo {
  price: number;
  probability: number;
  distance_pct: number;
}

export interface RiskScoreInfo {
  score: number;
  label: string;
  factors: string[];
}

export interface ConeWithLevels {
  cone: ConePoint[];
  liquidation_line: number;
  take_profit_line: number | null;
  stop_loss_line: number | null;
}

export interface PositionRiskResponse {
  asset: string;
  direction: string;
  entry_price: number;
  leverage: number;
  horizon: string;
  current_price: number;
  liquidation: LiquidationInfo;
  take_profit: TPSLInfo | null;
  stop_loss: TPSLInfo | null;
  pnl_distribution: {
    percentiles: Record<string, { price: number; pnl_pct: number; pnl_note?: string }>;
    expected_pnl_pct: number;
    probability_profitable: number;
  };
  cone_with_levels: ConeWithLevels;
  risk_score: RiskScoreInfo;
}

/** Derived data for the 3D cone visualization. */
export interface ConeRenderData {
  minPrice: number;
  maxPrice: number;
  currentPrice: number;
  volatility: number;
}
