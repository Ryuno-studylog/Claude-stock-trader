"""
市場データ関連エンドポイント
GET  /api/market/safety  — VIXチェック
POST /api/market/screen  — 銘柄スクリーニング
GET  /api/market/debug   — 1銘柄の生データ確認（デバッグ用）
"""

import traceback
import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.market_data import get_market_safety, screen_stocks, DEFAULT_UNIVERSE
from services.supabase_client import get_user_settings
from .deps import get_current_user

router = APIRouter(prefix="/api/market")


@router.get("/safety")
def market_safety():
    """VIXレベルと市場安全判定を返す"""
    return get_market_safety()


class ScreenRequest(BaseModel):
    min_volume_k: int   = 2000
    max_atr_pct:  float = 4.0
    trend:        str   = "any"   # "any" | "uptrend" | "downtrend"


@router.post("/screen")
def screen(req: ScreenRequest, user: dict = Depends(get_current_user)):
    """
    ユーザーのカスタムユニバース（未設定なら DEFAULT_UNIVERSE）をスクリーニングして返す
    """
    settings = get_user_settings(user["id"])
    universe = (
        settings["stock_universe"]
        if settings and settings.get("stock_universe")
        else DEFAULT_UNIVERSE
    )

    result = screen_stocks(
        universe=universe,
        min_volume_k=req.min_volume_k,
        max_atr_pct=req.max_atr_pct,
        trend=req.trend,
    )
    return {"stocks": result, "total": len(result)}


@router.get("/debug")
def debug():
    """
    トヨタ1銘柄でデータ取得を試みて生データを返す（デバッグ用・認証不要）
    問題の切り分け：yfinanceが動いているか / フィルタで弾かれているか
    """
    try:
        hist = yf.Ticker("7203.T").history(period="5d", auto_adjust=True)
        if hist.empty:
            return {"status": "empty", "detail": "yfinance returned empty DataFrame"}

        latest = hist.iloc[-1]
        return {
            "status":  "ok",
            "rows":    len(hist),
            "close":   float(latest["Close"]),
            "volume":  int(latest["Volume"]),
            "columns": list(hist.columns),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e), "trace": traceback.format_exc()}
