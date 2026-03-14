# Prism — Status

## Last Updated
2026-03-01

## Current Phase
Phase 3: Frontend Integration

## Completed
- [x] Synth API client (all /insights/* endpoints working)
- [x] AlphaLog collector on VPS with systemd (9/9 assets, hourly, local + Supabase)
- [x] MinerMind validation — PIVOTED (endpoints not on Pro plan)
- [x] Pivot from Forked (edge detection) to Prism (probability explorer + position risk)
- [x] ProbabilityEngine — percentile interpolation, probability_above/below/between, cone generation
- [x] PositionRiskAnalyzer — liquidation price, liquidation probability, P&L distribution, risk score
- [x] FastAPI server with caching — /api/health, /api/assets, /api/probability, /api/position-risk, /api/cone
- [x] Frontend design mockup built (3D probability cone, Explorer tab, Scanner tab)
- [x] Legacy analysis modules moved to legacy/
- [x] Frontend integrated — React + Vite + Three.js, ported from design, wired to FastAPI backend
- [x] Explorer UX refined — Above/Below/Between query modes with smart defaults
- [x] 3D probability cone rendering with real Synth percentile data

## In Progress
- [ ] Cone visual polish (scaling between horizons, grid fade, base cutoff)
- [ ] Deploy FastAPI to VPS alongside AlphaLog
- [ ] Deploy frontend to Vercel
- [ ] Demo video (60 seconds)
- [ ] One-page writeup

## Next Steps
- [ ] Deploy frontend to Vercel
- [ ] Deploy FastAPI to VPS alongside AlphaLog
- [ ] Demo video (60 seconds)
- [ ] One-page writeup
- [ ] README polish for judges

## VPS
- Service: alphalog (systemd)
- Location: /home/ubuntu/.polymarket/forked (needs rename to prism)
- Branch: develop
- Collecting: hourly, 9 assets, ~75 snapshots in Supabase as of Mar 1

## Architecture
```
backend/api/server.py          — FastAPI with 5-min caching SynthClient wrapper
backend/analysis/probability.py — ProbabilityEngine (percentile interpolation + cone)
backend/analysis/position_risk.py — PositionRiskAnalyzer (liquidation + P&L + risk score)
backend/synth_client.py        — Synth API client (14 methods, all /insights/* endpoints)
backend/config.py              — Assets, horizons, capability maps
backend/collectors/            — AlphaLog collector (alphalog.py, runner.py)
legacy/                        — Retired Forked analysis modules
frontend/                      — TO BE BUILT (React + Vite + Three.js)
```

## Key Files for Frontend Integration
- Frontend source to port: D:\Coding\Hackathon\hack-entry
- Backend API: python -m backend.api.run (port 8000)
- Frontend .env needs: VITE_API_URL pointing to backend
