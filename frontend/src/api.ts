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
  lower: number,
  upper: number,
  horizon: string = '24h',
): Promise<ProbabilityResponse> {
  return request<ProbabilityResponse>('/api/probability', {
    method: 'POST',
    body: JSON.stringify({ asset, lower, upper, horizon }),
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
  return request<PositionRiskResponse>('/api/position-risk', {
    method: 'POST',
    body: JSON.stringify({
      asset,
      entry_price,
      leverage,
      direction,
      take_profit: take_profit ?? null,
      stop_loss: stop_loss ?? null,
      horizon,
    }),
  });
}
