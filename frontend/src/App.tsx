import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  BarChart,
  Bar,
  Cell,
} from 'recharts';
import { Activity, AlertTriangle, ArrowDown, ArrowUp, CheckCircle2, Clock, Info, TrendingUp, Zap } from 'lucide-react';

const mockData = {
  "last_updated": "2026-03-10T14:00:00Z",
  "period": {
    "start": "2026-02-26T04:00:00Z",
    "end": "2026-03-10T14:00:00Z",
    "snapshots": 312,
    "hours_covered": 312
  },
  "synth_index": {
    "BTC": {
      "current": 62.5,
      "level": "ABOVE_AVERAGE",
      "mean": 52.3,
      "min": 18.4,
      "max": 84.2,
      "percentile_rank": 71,
      "history": [45.2, 47.8, 51.3, 49.1, 52.6, 55.8, 58.2, 54.9, 57.1, 60.3, 63.5, 61.2, 58.7, 55.4, 53.8, 56.1, 59.4, 62.8, 65.1, 63.7, 60.5, 58.9, 61.2, 62.5]
    },
    "ETH": {
      "current": 58.3,
      "level": "ABOVE_AVERAGE",
      "mean": 49.8,
      "min": 15.2,
      "max": 79.6,
      "percentile_rank": 65,
      "history": [42.1, 44.5, 48.2, 46.7, 50.1, 53.4, 55.8, 52.3, 54.6, 57.8, 60.2, 58.1, 55.4, 52.8, 51.2, 53.5, 56.8, 59.1, 61.4, 59.8, 57.2, 55.6, 57.8, 58.3]
    },
    "SOL": {
      "current": 55.1,
      "level": "ABOVE_AVERAGE",
      "mean": 51.1,
      "min": 20.5,
      "max": 82.1,
      "percentile_rank": 58,
      "history": [48.5, 50.2, 53.1, 51.8, 54.2, 56.5, 58.1, 55.4, 53.8, 55.2, 57.8, 56.1, 53.5, 51.2, 49.8, 52.1, 54.5, 56.8, 58.2, 56.5, 54.1, 52.8, 54.2, 55.1]
    },
    "XAU": {
      "current": 38.2,
      "level": "BELOW_AVERAGE",
      "mean": 35.5,
      "min": 12.1,
      "max": 68.4,
      "percentile_rank": 55,
      "history": [32.1, 33.5, 35.8, 34.2, 36.5, 38.1, 37.2, 35.8, 34.5, 36.2, 38.5, 37.1, 35.4, 33.8, 35.1, 36.4, 37.8, 38.5, 39.2, 38.1, 36.5, 37.2, 37.8, 38.2]
    },
    "SPY": {
      "current": 24.6,
      "level": "CALM",
      "mean": 28.2,
      "min": 10.5,
      "max": 55.2,
      "percentile_rank": 35,
      "history": [22.1, 23.5, 25.2, 24.1, 26.5, 27.8, 26.2, 24.8, 23.5, 25.1, 26.8, 25.4, 24.2, 22.8, 23.5, 24.8, 25.5, 26.2, 25.8, 24.5, 23.8, 24.2, 24.5, 24.6]
    },
    "NVDA": {
      "current": 71.2,
      "level": "ELEVATED",
      "mean": 55.8,
      "min": 22.4,
      "max": 88.5,
      "percentile_rank": 82,
      "history": [58.2, 60.5, 63.8, 61.2, 64.5, 67.8, 70.2, 68.5, 65.8, 67.2, 69.5, 71.8, 68.2, 65.5, 67.8, 70.1, 72.5, 74.2, 73.1, 71.5, 69.8, 70.5, 71.8, 71.2]
    },
    "GOOGL": {
      "current": 32.5,
      "level": "BELOW_AVERAGE",
      "mean": 30.2,
      "min": 11.2,
      "max": 52.8,
      "percentile_rank": 55,
      "history": [28.5, 29.8, 31.2, 30.5, 32.1, 33.5, 32.8, 31.2, 30.5, 31.8, 33.2, 32.1, 30.8, 29.5, 30.8, 31.5, 32.2, 33.1, 32.8, 32.1, 31.5, 32.2, 32.8, 32.5]
    },
    "TSLA": {
      "current": 66.8,
      "level": "ABOVE_AVERAGE",
      "mean": 58.5,
      "min": 25.8,
      "max": 85.2,
      "percentile_rank": 68,
      "history": [55.2, 57.5, 60.8, 58.2, 61.5, 64.8, 67.2, 65.5, 62.8, 64.2, 66.5, 68.2, 65.5, 62.8, 64.5, 66.8, 68.2, 69.5, 68.1, 66.5, 65.2, 66.8, 67.5, 66.8]
    },
    "AAPL": {
      "current": 28.4,
      "level": "CALM",
      "mean": 26.8,
      "min": 10.8,
      "max": 48.5,
      "percentile_rank": 52,
      "history": [24.2, 25.5, 27.1, 26.2, 28.5, 29.2, 28.1, 26.8, 25.5, 27.2, 28.8, 27.5, 26.2, 25.1, 26.5, 27.2, 28.1, 28.8, 28.5, 27.8, 27.2, 27.8, 28.2, 28.4]
    }
  },
  "distribution_metrics": {
    "BTC": {"bias": 0.0132, "width": 0.0385, "skew": 1.15, "tail_fatness": 2.82, "upper_tail_risk": 0.45, "lower_tail_risk": 0.38, "density_concentration": 0.31, "regime": "NORMAL"},
    "ETH": {"bias": 0.0098, "width": 0.0452, "skew": 0.92, "tail_fatness": 3.15, "upper_tail_risk": 0.42, "lower_tail_risk": 0.52, "density_concentration": 0.28, "regime": "NORMAL"},
    "SOL": {"bias": -0.0045, "width": 0.0618, "skew": 0.78, "tail_fatness": 3.45, "upper_tail_risk": 0.38, "lower_tail_risk": 0.61, "density_concentration": 0.25, "regime": "STRESSED"},
    "XAU": {"bias": 0.0025, "width": 0.0182, "skew": 1.08, "tail_fatness": 2.45, "upper_tail_risk": 0.35, "lower_tail_risk": 0.32, "density_concentration": 0.38, "regime": "NORMAL"},
    "SPY": {"bias": -0.0018, "width": 0.0125, "skew": 0.95, "tail_fatness": 2.12, "upper_tail_risk": 0.28, "lower_tail_risk": 0.31, "density_concentration": 0.42, "regime": "COMPRESSED"},
    "NVDA": {"bias": 0.0215, "width": 0.0395, "skew": 1.42, "tail_fatness": 3.85, "upper_tail_risk": 0.68, "lower_tail_risk": 0.25, "density_concentration": 0.19, "regime": "STRESSED"},
    "GOOGL": {"bias": -0.0032, "width": 0.0158, "skew": 0.88, "tail_fatness": 2.28, "upper_tail_risk": 0.30, "lower_tail_risk": 0.35, "density_concentration": 0.39, "regime": "NORMAL"},
    "TSLA": {"bias": 0.0178, "width": 0.0342, "skew": 1.35, "tail_fatness": 3.52, "upper_tail_risk": 0.58, "lower_tail_risk": 0.28, "density_concentration": 0.22, "regime": "STRESSED"},
    "AAPL": {"bias": -0.0012, "width": 0.0138, "skew": 0.98, "tail_fatness": 2.18, "upper_tail_risk": 0.25, "lower_tail_risk": 0.28, "density_concentration": 0.41, "regime": "COMPRESSED"}
  },
  "edges": {
    "open": [
      {"asset": "BTC", "edge_type": "simple_probability", "direction": "UP", "confidence": "HIGH", "edge_size": 0.154, "synth_probability": 0.72, "polymarket_probability": 0.566, "deadline": "2026-03-10T22:00:00Z"},
      {"asset": "ETH", "edge_type": "tail_risk_underpriced", "direction": "DOWN_RISK", "confidence": "MEDIUM", "edge_size": 0.088, "synth_probability": 0.61, "polymarket_probability": 0.79, "deadline": "2026-03-10T15:00:00Z"},
      {"asset": "SOL", "edge_type": "skew_mismatch", "direction": "DOWN", "confidence": "MEDIUM", "edge_size": 0.112, "synth_probability": 0.58, "polymarket_probability": 0.692, "deadline": "2026-03-10T22:00:00Z"},
      {"asset": "SPY", "edge_type": "simple_probability", "direction": "DOWN", "confidence": "HIGH", "edge_size": 0.168, "synth_probability": 0.38, "polymarket_probability": 0.548, "deadline": "2026-03-10T22:00:00Z"},
      {"asset": "NVDA", "edge_type": "uncertainty_underpriced", "direction": "UNCERTAIN", "confidence": "HIGH", "edge_size": 0.145, "synth_probability": 0.52, "polymarket_probability": 0.665, "deadline": "2026-03-10T22:00:00Z"}
    ],
    "performance": {
      "total_resolved": 187,
      "correct": 112,
      "incorrect": 75,
      "hit_rate": 0.599,
      "total_pnl": 28.45,
      "sharpe_ratio": 1.42,
      "by_edge_type": {
        "simple_probability": {"hit_rate": 0.62, "n": 85, "pnl": 15.2},
        "tail_risk_underpriced": {"hit_rate": 0.55, "n": 42, "pnl": 5.8},
        "skew_mismatch": {"hit_rate": 0.58, "n": 35, "pnl": 4.5},
        "uncertainty_underpriced": {"hit_rate": 0.64, "n": 25, "pnl": 2.95}
      },
      "by_confidence": {
        "HIGH": {"hit_rate": 0.68, "n": 62, "pnl": 18.5},
        "MEDIUM": {"hit_rate": 0.57, "n": 78, "pnl": 8.2},
        "LOW": {"hit_rate": 0.51, "n": 47, "pnl": 1.75}
      },
      "cumulative_pnl": [0, 0.82, 0.32, 1.15, 0.65, 1.48, 2.31, 1.81, 2.64, 3.47, 3.97, 4.80, 4.30, 5.13, 5.96, 6.79, 6.29, 7.12, 7.95, 8.78, 9.61, 9.11, 9.94, 10.77, 11.60, 12.43, 11.93, 12.76, 13.59, 14.42, 15.25, 14.75, 15.58, 16.41, 17.24, 18.07, 18.90, 18.40, 19.23, 20.06, 20.89, 21.72, 21.22, 22.05, 22.88, 23.71, 24.54, 25.37, 24.87, 25.70, 26.53, 27.36, 28.45]
    }
  },
  "cross_asset": {
    "crypto": {
      "consensus": 0.72,
      "consensus_level": "MEDIUM",
      "avg_synth_index": 58.6,
      "outlier": null,
      "similarity_matrix": {
        "assets": ["BTC", "ETH", "SOL"],
        "matrix": [[1.0, 0.78, 0.65], [0.78, 1.0, 0.72], [0.65, 0.72, 1.0]]
      }
    },
    "equities": {
      "consensus": 0.35,
      "consensus_level": "LOW",
      "avg_synth_index": 44.7,
      "outlier": {"asset": "NVDA", "reason": "Tail fatness 2x group average, density concentration below 0.20"},
      "similarity_matrix": {
        "assets": ["SPY", "NVDA", "GOOGL", "TSLA", "AAPL"],
        "matrix": [[1.0, 0.42, 0.85, 0.38, 0.88], [0.42, 1.0, 0.35, 0.72, 0.38], [0.85, 0.35, 1.0, 0.32, 0.82], [0.38, 0.72, 0.32, 1.0, 0.35], [0.88, 0.38, 0.82, 0.35, 1.0]]
      }
    },
    "regime": "RISK_OFF",
    "regime_description": "Both asset groups showing elevated uncertainty. Crypto bullish bias with wide distributions, equities mixed with NVDA diverging significantly."
  },
  "anomalies": [
    {"timestamp": "2026-03-10T14:00:00Z", "asset": "BTC", "type": "skew_flip", "severity": "MEDIUM", "previous": 0.88, "current": 1.15, "description": "BTC skew flipped from bearish to bullish"},
    {"timestamp": "2026-03-10T13:00:00Z", "asset": "NVDA", "type": "tail_fattening", "severity": "HIGH", "previous": 2.85, "current": 3.85, "description": "NVDA tail fatness surged 35% \u2014 elevated event risk"},
    {"timestamp": "2026-03-10T12:00:00Z", "asset": "ETH", "type": "volatility_compression", "severity": "LOW", "previous": 0.052, "current": 0.045, "description": "ETH forecast width narrowing \u2014 possible breakout setup"},
    {"timestamp": "2026-03-10T11:00:00Z", "asset": "SOL", "type": "regime_change", "severity": "MEDIUM", "previous": "NORMAL", "current": "STRESSED", "description": "SOL moved to STRESSED regime \u2014 width and tail fatness elevated"},
    {"timestamp": "2026-03-10T09:00:00Z", "asset": "TSLA", "type": "volatility_expansion", "severity": "MEDIUM", "previous": 0.025, "current": 0.034, "description": "TSLA distribution widening 36%"},
    {"timestamp": "2026-03-10T08:00:00Z", "asset": "BTC", "type": "tail_fattening", "severity": "LOW", "previous": 2.55, "current": 2.82, "description": "BTC tails getting heavier \u2014 monitor for escalation"}
  ]
};

// Helper functions for styling
const getLevelColor = (level: string) => {
  switch (level) {
    case 'CALM': return 'text-[#22c55e]';
    case 'BELOW_AVERAGE': return 'text-[#3b82f6]';
    case 'ABOVE_AVERAGE': return 'text-[#f59e0b]';
    case 'ELEVATED':
    case 'EXTREME': return 'text-[#ef4444]';
    default: return 'text-[#94a3b8]';
  }
};

const getLevelBg = (level: string) => {
  switch (level) {
    case 'CALM': return 'bg-[#22c55e]/10 border-[#22c55e]/20';
    case 'BELOW_AVERAGE': return 'bg-[#3b82f6]/10 border-[#3b82f6]/20';
    case 'ABOVE_AVERAGE': return 'bg-[#f59e0b]/10 border-[#f59e0b]/20';
    case 'ELEVATED':
    case 'EXTREME': return 'bg-[#ef4444]/10 border-[#ef4444]/20';
    default: return 'bg-[#1e1e2e] border-[#1e1e2e]';
  }
};

const getRegimeColor = (regime: string) => {
  switch (regime) {
    case 'NORMAL': return 'bg-[#22c55e]/20 text-[#22c55e] border-[#22c55e]/30';
    case 'COMPRESSED': return 'bg-[#f59e0b]/20 text-[#f59e0b] border-[#f59e0b]/30';
    case 'STRESSED': return 'bg-[#ef4444]/20 text-[#ef4444] border-[#ef4444]/30';
    default: return 'bg-gray-800 text-gray-300 border-gray-700';
  }
};

const getConfidenceColor = (conf: string) => {
  switch (conf) {
    case 'HIGH': return 'bg-[#22c55e]/20 text-[#22c55e] border-[#22c55e]/30';
    case 'MEDIUM': return 'bg-[#f59e0b]/20 text-[#f59e0b] border-[#f59e0b]/30';
    case 'LOW': return 'bg-[#94a3b8]/20 text-[#94a3b8] border-[#94a3b8]/30';
    default: return 'bg-gray-800 text-gray-300 border-gray-700';
  }
};

const getSeverityColor = (sev: string) => {
  switch (sev) {
    case 'HIGH': return 'bg-[#ef4444]/20 text-[#ef4444] border-[#ef4444]/30';
    case 'MEDIUM': return 'bg-[#f59e0b]/20 text-[#f59e0b] border-[#f59e0b]/30';
    case 'LOW': return 'bg-[#94a3b8]/20 text-[#94a3b8] border-[#94a3b8]/30';
    default: return 'bg-gray-800 text-gray-300 border-gray-700';
  }
};

const getHeatmapColor = (val: number) => {
  if (val > 0.8) return 'bg-[#3b82f6] text-white';
  if (val > 0.6) return 'bg-[#3b82f6]/60 text-white';
  if (val > 0.4) return 'bg-[#1e1e2e] text-[#94a3b8]';
  if (val > 0.2) return 'bg-[#ef4444]/60 text-white';
  return 'bg-[#ef4444] text-white';
};

export default function App() {
  // Prepare data for Synth-Index History Chart
  const historyData = mockData.synth_index.BTC.history.map((_, i) => ({
    hour: i,
    BTC: mockData.synth_index.BTC.history[i],
    ETH: mockData.synth_index.ETH.history[i],
    SOL: mockData.synth_index.SOL.history[i],
  }));

  // Prepare data for Radar Chart (normalized for visual comparison)
  const radarData = [
    {
      subject: 'Width',
      BTC: (mockData.distribution_metrics.BTC.width / 0.07) * 100,
      ETH: (mockData.distribution_metrics.ETH.width / 0.07) * 100,
      SOL: (mockData.distribution_metrics.SOL.width / 0.07) * 100,
      fullMark: 100,
    },
    {
      subject: 'Skew',
      BTC: (Math.abs(mockData.distribution_metrics.BTC.skew) / 1.5) * 100,
      ETH: (Math.abs(mockData.distribution_metrics.ETH.skew) / 1.5) * 100,
      SOL: (Math.abs(mockData.distribution_metrics.SOL.skew) / 1.5) * 100,
      fullMark: 100,
    },
    {
      subject: 'Tail Fatness',
      BTC: (mockData.distribution_metrics.BTC.tail_fatness / 4) * 100,
      ETH: (mockData.distribution_metrics.ETH.tail_fatness / 4) * 100,
      SOL: (mockData.distribution_metrics.SOL.tail_fatness / 4) * 100,
      fullMark: 100,
    },
    {
      subject: 'Density',
      BTC: (mockData.distribution_metrics.BTC.density_concentration / 0.5) * 100,
      ETH: (mockData.distribution_metrics.ETH.density_concentration / 0.5) * 100,
      SOL: (mockData.distribution_metrics.SOL.density_concentration / 0.5) * 100,
      fullMark: 100,
    },
    {
      subject: 'Abs Bias',
      BTC: (Math.abs(mockData.distribution_metrics.BTC.bias) / 0.03) * 100,
      ETH: (Math.abs(mockData.distribution_metrics.ETH.bias) / 0.03) * 100,
      SOL: (Math.abs(mockData.distribution_metrics.SOL.bias) / 0.03) * 100,
      fullMark: 100,
    },
  ];

  // Prepare data for Hit Rate Bar Chart
  const hitRateData = Object.entries(mockData.edges.performance.by_edge_type).map(([key, val]) => ({
    name: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    rate: val.hit_rate * 100,
  }));

  // Prepare data for Cumulative P&L
  const pnlData = mockData.edges.performance.cumulative_pnl.map((val, i) => ({
    trade: i,
    pnl: val,
  }));

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-[#e2e8f0] font-sans p-6 pb-20">
      <div className="max-w-[1600px] mx-auto space-y-8">

        {/* HEADER */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-[#1e1e2e] pb-6">
          <div>
            <h1 className="text-4xl font-black tracking-tighter text-white flex items-center gap-3">
              <Zap className="w-8 h-8 text-[#3b82f6]" fill="currentColor" />
              FORKED
            </h1>
            <p className="text-[#94a3b8] text-sm mt-1 font-mono tracking-wide uppercase">Where probability paths diverge, edge emerges</p>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#22c55e] animate-pulse"></div>
              <span className="text-[#94a3b8] text-xs font-mono">Last updated: 2 min ago</span>
            </div>
            <div className="flex items-center gap-4 bg-[#12121a] border border-[#1e1e2e] px-5 py-3 rounded-xl shadow-lg">
              <div className="flex flex-col">
                <span className="text-[#94a3b8] text-[10px] font-mono uppercase tracking-wider">BTC Synth-Index</span>
                <span className={`text-2xl font-bold leading-none mt-1 ${getLevelColor(mockData.synth_index.BTC.level)}`}>
                  {mockData.synth_index.BTC.current.toFixed(1)}
                </span>
              </div>
              {/* Mini Gauge Indicator */}
              <div className="relative w-16 h-2 mt-1">
                <div className="w-full h-full bg-[#1e1e2e] rounded-full overflow-hidden flex">
                  <div className="h-full bg-[#22c55e]" style={{ width: '30%' }}></div>
                  <div className="h-full bg-[#3b82f6]" style={{ width: '20%' }}></div>
                  <div className="h-full bg-[#f59e0b]" style={{ width: '20%' }}></div>
                  <div className="h-full bg-[#ef4444]" style={{ width: '30%' }}></div>
                </div>
                {/* Marker */}
                <div
                  className="absolute top-1/2 -translate-y-1/2 w-1 h-3 bg-white shadow-sm rounded-full"
                  style={{ left: `calc(${mockData.synth_index.BTC.current}% - 2px)` }}
                ></div>
              </div>
            </div>
          </div>
        </header>

        {/* SECTION 1: SYNTH-INDEX OVERVIEW */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-5 h-5 text-[#3b82f6]" />
            <h2 className="text-lg font-semibold tracking-wide">Synth-Index Overview</h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 xl:grid-cols-9 gap-3">
            {Object.entries(mockData.synth_index).map(([asset, data]) => {
              const sparklineData = data.history.map((val, i) => ({ i, val }));
              const isPositive = data.current > data.history[0];
              const strokeColor = isPositive ? '#22c55e' : '#ef4444';

              return (
                <div key={asset} className={`bg-[#12121a] border rounded-xl p-4 flex flex-col justify-between ${getLevelBg(data.level)} transition-colors`}>
                  <div className="flex justify-between items-start">
                    <span className="font-bold text-sm">{asset}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-bold border ${getLevelBg(data.level)} ${getLevelColor(data.level)}`}>
                      {data.level.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="mt-3 mb-2">
                    <span className={`text-3xl font-light tracking-tighter ${getLevelColor(data.level)}`}>
                      {data.current.toFixed(1)}
                    </span>
                  </div>
                  <div className="h-10 w-full mt-auto">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={sparklineData}>
                        <Line type="monotone" dataKey="val" stroke={strokeColor} strokeWidth={2} dot={false} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5 h-64 mt-4">
            <h3 className="text-xs font-mono text-[#94a3b8] uppercase tracking-wider mb-4">Crypto Majors 24h History</h3>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historyData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" vertical={false} />
                <XAxis dataKey="hour" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `-${24-val}h`} />
                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} domain={['dataMin - 5', 'dataMax + 5']} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#12121a', borderColor: '#1e1e2e', borderRadius: '8px' }}
                  itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
                  labelStyle={{ display: 'none' }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                <Line type="monotone" dataKey="BTC" stroke="#f59e0b" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="ETH" stroke="#3b82f6" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="SOL" stroke="#10b981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* SECTION 2 & 3 GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* SECTION 2: DISTRIBUTION SHAPE */}
          <section className="lg:col-span-5 space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-5 h-5 text-[#3b82f6]" />
              <h2 className="text-lg font-semibold tracking-wide">Distribution Shape</h2>
            </div>

            <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-[#94a3b8] uppercase bg-[#1e1e2e]/50 border-b border-[#1e1e2e]">
                    <tr>
                      <th className="px-4 py-3 font-mono">Asset</th>
                      <th className="px-4 py-3 font-mono text-right">Bias</th>
                      <th className="px-4 py-3 font-mono text-right">Width</th>
                      <th className="px-4 py-3 font-mono text-right">Skew</th>
                      <th className="px-4 py-3 font-mono text-center">Regime</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(mockData.distribution_metrics).slice(0, 5).map(([asset, metrics]) => (
                      <tr key={asset} className="border-b border-[#1e1e2e]/50 hover:bg-[#1e1e2e]/30 transition-colors">
                        <td className="px-4 py-3 font-bold">{asset}</td>
                        <td className={`px-4 py-3 text-right font-mono ${metrics.bias > 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                          {metrics.bias > 0 ? '+' : ''}{(metrics.bias * 100).toFixed(2)}%
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-[#e2e8f0]">{(metrics.width * 100).toFixed(1)}%</td>
                        <td className="px-4 py-3 text-right font-mono text-[#e2e8f0]">{metrics.skew.toFixed(2)}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`text-[10px] px-2 py-1 rounded-full font-bold border ${getRegimeColor(metrics.regime)}`}>
                            {metrics.regime}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="h-64 p-4 border-t border-[#1e1e2e]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                    <PolarGrid stroke="#1e1e2e" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'monospace' }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                    <Radar name="BTC" dataKey="BTC" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.2} strokeWidth={2} />
                    <Radar name="ETH" dataKey="ETH" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} strokeWidth={2} />
                    <Radar name="SOL" dataKey="SOL" stroke="#10b981" fill="#10b981" fillOpacity={0.2} strokeWidth={2} />
                    <Legend wrapperStyle={{ fontSize: '12px' }} />
                    <Tooltip contentStyle={{ backgroundColor: '#12121a', borderColor: '#1e1e2e', borderRadius: '8px' }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          {/* SECTION 3: EDGE DETECTION & PERFORMANCE */}
          <section className="lg:col-span-7 space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-5 h-5 text-[#22c55e]" />
              <h2 className="text-lg font-semibold tracking-wide">Edge Detection & Performance</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full">
              {/* Open Edges */}
              <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl flex flex-col">
                <div className="p-4 border-b border-[#1e1e2e] flex justify-between items-center">
                  <h3 className="text-sm font-bold">Open Edges vs Polymarket</h3>
                  <span className="bg-[#3b82f6]/20 text-[#3b82f6] text-xs px-2 py-1 rounded-full font-bold">{mockData.edges.open.length} Active</span>
                </div>
                <div className="overflow-y-auto flex-1 p-2 space-y-2">
                  {mockData.edges.open.map((edge, i) => (
                    <div key={i} className="bg-[#1e1e2e]/40 border border-[#1e1e2e] rounded-lg p-3 hover:bg-[#1e1e2e] transition-colors">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-lg">{edge.asset}</span>
                          {edge.direction === 'UP' && <ArrowUp className="w-4 h-4 text-[#22c55e]" />}
                          {edge.direction === 'DOWN' && <ArrowDown className="w-4 h-4 text-[#ef4444]" />}
                          {edge.direction === 'DOWN_RISK' && <ArrowDown className="w-4 h-4 text-[#ef4444]" />}
                          {edge.direction === 'UNCERTAIN' && <Activity className="w-4 h-4 text-[#f59e0b]" />}
                        </div>
                        <span className={`text-[10px] px-2 py-1 rounded font-bold border ${getConfidenceColor(edge.confidence)}`}>
                          {edge.confidence} CONF
                        </span>
                      </div>
                      <div className="text-xs text-[#94a3b8] font-mono mb-3">{edge.edge_type.replace(/_/g, ' ').toUpperCase()}</div>

                      <div className="grid grid-cols-3 gap-2 text-center">
                        <div className="bg-[#0a0a0f] rounded p-2 border border-[#1e1e2e]">
                          <div className="text-[10px] text-[#94a3b8] uppercase mb-1">Synth</div>
                          <div className="font-mono font-bold text-[#3b82f6]">{(edge.synth_probability * 100).toFixed(1)}%</div>
                        </div>
                        <div className="bg-[#0a0a0f] rounded p-2 border border-[#1e1e2e]">
                          <div className="text-[10px] text-[#94a3b8] uppercase mb-1">Poly</div>
                          <div className="font-mono font-bold text-[#e2e8f0]">{(edge.polymarket_probability * 100).toFixed(1)}%</div>
                        </div>
                        <div className="bg-[#22c55e]/10 rounded p-2 border border-[#22c55e]/20">
                          <div className="text-[10px] text-[#22c55e] uppercase mb-1">Edge</div>
                          <div className="font-mono font-bold text-[#22c55e]">{(edge.edge_size * 100).toFixed(1)}%</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Performance Panel */}
              <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-4 flex flex-col">
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div>
                    <div className="text-xs text-[#94a3b8] font-mono uppercase mb-1">Hit Rate</div>
                    <div className="text-2xl font-bold text-[#22c55e]">{(mockData.edges.performance.hit_rate * 100).toFixed(1)}%</div>
                  </div>
                  <div>
                    <div className="text-xs text-[#94a3b8] font-mono uppercase mb-1">Total P&L</div>
                    <div className="text-2xl font-bold text-[#22c55e]">+{mockData.edges.performance.total_pnl.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-[#94a3b8] font-mono uppercase mb-1">Sharpe</div>
                    <div className="text-2xl font-bold text-white">{mockData.edges.performance.sharpe_ratio.toFixed(2)}</div>
                  </div>
                </div>

                <div className="flex-1 min-h-[120px] mb-4">
                  <h4 className="text-[10px] text-[#94a3b8] font-mono uppercase mb-2">Cumulative P&L</h4>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={pnlData}>
                      <Line type="monotone" dataKey="pnl" stroke="#22c55e" strokeWidth={2} dot={false} />
                      <YAxis domain={['auto', 'auto']} hide />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#12121a', borderColor: '#1e1e2e', borderRadius: '8px' }}
                        labelStyle={{ display: 'none' }}
                        formatter={(value: number | undefined) => [`+${(value ?? 0).toFixed(2)}`, 'P&L']}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <div className="flex-1 min-h-[120px]">
                  <h4 className="text-[10px] text-[#94a3b8] font-mono uppercase mb-2">Hit Rate by Edge Type</h4>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={hitRateData} layout="vertical" margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                      <XAxis type="number" domain={[0, 100]} hide />
                      <YAxis dataKey="name" type="category" width={120} tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
                      <Tooltip cursor={{ fill: '#1e1e2e' }} contentStyle={{ backgroundColor: '#12121a', borderColor: '#1e1e2e', borderRadius: '8px' }} />
                      <Bar dataKey="rate" radius={[0, 4, 4, 0]} barSize={12}>
                        {hitRateData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.rate > 60 ? '#22c55e' : '#3b82f6'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* SECTION 4 & 5 GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* SECTION 4: CROSS-ASSET CORRELATION */}
          <section className="lg:col-span-7 space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-5 h-5 text-[#f59e0b]" />
              <h2 className="text-lg font-semibold tracking-wide">Cross-Asset Correlation</h2>
            </div>

            <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5">
              <div className="flex flex-col md:flex-row gap-8">

                {/* Crypto Heatmap */}
                <div className="flex-1">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-sm font-bold">Crypto Similarity</h3>
                    <span className="text-xs font-mono text-[#94a3b8]">Consensus: {(mockData.cross_asset.crypto.consensus * 100).toFixed(0)}%</span>
                  </div>
                  <div className="grid grid-cols-4 gap-1">
                    <div className="col-span-1"></div>
                    {mockData.cross_asset.crypto.similarity_matrix.assets.map(a => (
                      <div key={`h-${a}`} className="text-center text-xs font-mono text-[#94a3b8] py-1">{a}</div>
                    ))}

                    {mockData.cross_asset.crypto.similarity_matrix.assets.map((asset, i) => (
                      <React.Fragment key={`row-${asset}`}>
                        <div className="text-right text-xs font-mono text-[#94a3b8] pr-2 py-2 flex items-center justify-end">{asset}</div>
                        {mockData.cross_asset.crypto.similarity_matrix.matrix[i].map((val, j) => (
                          <div
                            key={`cell-${i}-${j}`}
                            className={`rounded flex items-center justify-center text-[10px] font-mono font-bold h-8 ${getHeatmapColor(val)}`}
                            title={`${asset} vs ${mockData.cross_asset.crypto.similarity_matrix.assets[j]}: ${val.toFixed(2)}`}
                          >
                            {val.toFixed(2)}
                          </div>
                        ))}
                      </React.Fragment>
                    ))}
                  </div>
                </div>

                {/* Equities Heatmap */}
                <div className="flex-[1.5]">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-sm font-bold">Equities Similarity</h3>
                    <span className="text-xs font-mono text-[#94a3b8]">Consensus: {(mockData.cross_asset.equities.consensus * 100).toFixed(0)}%</span>
                  </div>
                  <div className="grid grid-cols-6 gap-1">
                    <div className="col-span-1"></div>
                    {mockData.cross_asset.equities.similarity_matrix.assets.map(a => (
                      <div key={`h-${a}`} className="text-center text-[10px] font-mono text-[#94a3b8] py-1">{a}</div>
                    ))}

                    {mockData.cross_asset.equities.similarity_matrix.assets.map((asset, i) => (
                      <React.Fragment key={`row-${asset}`}>
                        <div className="text-right text-[10px] font-mono text-[#94a3b8] pr-2 py-1.5 flex items-center justify-end">{asset}</div>
                        {mockData.cross_asset.equities.similarity_matrix.matrix[i].map((val, j) => (
                          <div
                            key={`cell-${i}-${j}`}
                            className={`rounded flex items-center justify-center text-[9px] font-mono font-bold h-6 ${getHeatmapColor(val)}`}
                            title={`${asset} vs ${mockData.cross_asset.equities.similarity_matrix.assets[j]}: ${val.toFixed(2)}`}
                          >
                            {val.toFixed(2)}
                          </div>
                        ))}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-[#1e1e2e] flex flex-col md:flex-row gap-4">
                <div className="flex-1 bg-[#1e1e2e]/30 rounded-lg p-4 border border-[#1e1e2e]">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="bg-[#ef4444]/20 text-[#ef4444] border border-[#ef4444]/30 px-2 py-0.5 rounded text-xs font-bold tracking-wider">
                      {mockData.cross_asset.regime}
                    </span>
                    <span className="text-xs text-[#94a3b8] font-mono uppercase">Current Regime</span>
                  </div>
                  <p className="text-sm text-[#e2e8f0] leading-relaxed">
                    {mockData.cross_asset.regime_description}
                  </p>
                </div>

                {mockData.cross_asset.equities.outlier && (
                  <div className="flex-1 bg-[#f59e0b]/10 rounded-lg p-4 border border-[#f59e0b]/30">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="w-4 h-4 text-[#f59e0b]" />
                      <span className="text-sm font-bold text-[#f59e0b]">Outlier Detected: {mockData.cross_asset.equities.outlier.asset}</span>
                    </div>
                    <p className="text-sm text-[#f59e0b]/80 leading-relaxed">
                      {mockData.cross_asset.equities.outlier.reason}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* SECTION 5: ANOMALY FEED */}
          <section className="lg:col-span-5 space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-5 h-5 text-[#94a3b8]" />
              <h2 className="text-lg font-semibold tracking-wide">Live Anomaly Feed</h2>
            </div>

            <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5 h-[420px] overflow-y-auto relative">
              <div className="absolute left-[27px] top-5 bottom-5 w-px bg-[#1e1e2e]"></div>
              <div className="space-y-6 relative">
                {mockData.anomalies.map((anomaly, i) => (
                  <div key={i} className="flex gap-4 relative">
                    <div className={`w-4 h-4 rounded-full mt-1 z-10 border-2 border-[#12121a] ${
                      anomaly.severity === 'HIGH' ? 'bg-[#ef4444]' :
                      anomaly.severity === 'MEDIUM' ? 'bg-[#f59e0b]' : 'bg-[#94a3b8]'
                    }`}></div>
                    <div className="flex-1 bg-[#1e1e2e]/30 border border-[#1e1e2e] rounded-lg p-3 hover:bg-[#1e1e2e]/50 transition-colors">
                      <div className="flex justify-between items-start mb-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold">{anomaly.asset}</span>
                          <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold border uppercase ${getSeverityColor(anomaly.severity)}`}>
                            {anomaly.severity}
                          </span>
                        </div>
                        <span className="text-xs text-[#94a3b8] font-mono">
                          {new Date(anomaly.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <div className="text-xs text-[#3b82f6] font-mono mb-2">{anomaly.type.replace('_', ' ').toUpperCase()}</div>
                      <p className="text-sm text-[#e2e8f0]">{anomaly.description}</p>

                      {anomaly.previous && anomaly.current && (
                        <div className="mt-3 flex items-center gap-3 text-xs font-mono bg-[#0a0a0f] p-2 rounded border border-[#1e1e2e] inline-flex">
                          <span className="text-[#94a3b8]">{typeof anomaly.previous === 'number' ? anomaly.previous.toFixed(3) : anomaly.previous}</span>
                          <ArrowUp className="w-3 h-3 text-[#94a3b8] rotate-90" />
                          <span className="text-white font-bold">{typeof anomaly.current === 'number' ? anomaly.current.toFixed(3) : anomaly.current}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>

        {/* FOOTER */}
        <footer className="pt-8 pb-4 border-t border-[#1e1e2e] flex flex-col md:flex-row justify-between items-center gap-4 text-xs font-mono text-[#94a3b8]">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4" />
            <span>Built on Synth API (Bittensor Subnet 50)</span>
          </div>
          <div>
            Synth Predictive Intelligence Hackathon 2026
          </div>
        </footer>

      </div>
    </div>
  );
}
