/**
 * バックエンド API クライアント
 * すべてのリクエストに Authorization: Bearer <token> を付与する
 */
import { getAuthToken } from "./supabase";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function authHeaders(): Promise<HeadersInit> {
  const token = await getAuthToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// ── 市場データ ──────────────────────────────────────────

export async function fetchSafety() {
  const res = await fetch(`${API_URL}/api/market/safety`);
  return res.json();
}

export async function fetchScreen(params: {
  min_volume_k: number;
  max_atr_pct: number;
  trend: string;
}) {
  const res = await fetch(`${API_URL}/api/market/screen`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ── 計画生成（SSEストリーミング） ─────────────────────────

export interface PlanRequest {
  budget: number;
  holding_period: string;
  risk_tolerance: string;
  review_note: string;
  watchlist: object[];
  vix_info: object;
  language: string;
}

/**
 * SSEストリームを開いてテキストチャンクを非同期で yield する
 * @example
 * for await (const chunk of streamPlan(req)) { setText(t => t + chunk) }
 */
export async function* streamPlan(req: PlanRequest): AsyncGenerator<string> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/api/plan/generate`, {
    method: "POST",
    headers,
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6);
      if (payload === "[DONE]") return;
      try {
        const { text } = JSON.parse(payload);
        if (text) yield text;
      } catch {
        // パースエラーは無視
      }
    }
  }
}

// ── ユーザー ──────────────────────────────────────────

export async function fetchProfile() {
  const res = await fetch(`${API_URL}/api/user/profile`, {
    headers: await authHeaders(),
  });
  return res.json();
}

export async function fetchUserSettings() {
  const res = await fetch(`${API_URL}/api/user/settings`, {
    headers: await authHeaders(),
  });
  return res.json();
}

export async function saveUserSettings(settings: object) {
  const res = await fetch(`${API_URL}/api/user/settings`, {
    method: "PUT",
    headers: await authHeaders(),
    body: JSON.stringify(settings),
  });
  return res.json();
}

export async function fetchHistory() {
  const res = await fetch(`${API_URL}/api/user/history`, {
    headers: await authHeaders(),
  });
  return res.json();
}

// ── 課金 ──────────────────────────────────────────────

export async function createCheckout(price_id: string) {
  const res = await fetch(`${API_URL}/api/billing/checkout`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify({ price_id }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail);
  return data as { url: string };
}
