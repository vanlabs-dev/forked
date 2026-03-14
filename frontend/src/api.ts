import type { Asset, ConeResponse, ProbabilityResponse, PositionRiskResponse } from './types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
  } catch {
    throw new Error('Cannot connect to Prism API');
  }

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    const message =
      typeof detail?.detail === 'string'
        ? detail.detail
        : detail?.detail?.error ?? `API error ${res.status}`;
    throw new Error(message);
  }

  return res.json();
}

export async function fetchAssets(): Promise<Asset[]> {
  const data = await request<{ assets: Asset[] }>('/api/assets');
  return data.assets;
}

export async function fetchCone(asset: string, horizon: string = '24h'): Promise<ConeResponse> {
  return request<ConeResponse>(`/api/cone/${asset}?horizon=${horizon}`);
}

export async function fetchProbability(
  asset: string,
  lower: number | undefined,
  upper: number | undefined,
  horizon: string = '24h',
): Promise<ProbabilityResponse> {
  const body: Record<string, unknown> = { asset, horizon };
  if (lower != null) body.lower = lower;
  if (upper != null) body.upper = upper;
  return request<ProbabilityResponse>('/api/probability', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function fetchPositionRisk(
  asset: string,
  entry_price: number,
  leverage: number,
  direction: string,
  take_profit?: number,
  stop_loss?: number,
  horizon: string = '24h',
): Promise<PositionRiskResponse> {
  // Treat 0 as "not set" — a $0 TP/SL is nonsensical
  const tp = take_profit && take_profit > 0 ? take_profit : null;
  const sl = stop_loss && stop_loss > 0 ? stop_loss : null;

  const body = {
    asset,
    entry_price,
    leverage,
    direction,
    take_profit: tp,
    stop_loss: sl,
    horizon,
  };
  console.log('[Prism] POST /api/position-risk', body);

  return request<PositionRiskResponse>('/api/position-risk', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}
