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
    """トヨタ1銘柄の生データ確認（認証不要）"""
    try:
        hist = yf.Ticker("7203.T").history(period="5d", auto_adjust=True)
        if hist.empty:
            return {"status": "empty"}
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


@router.get("/debug2")
def debug2():
    """_calc_record をトヨタで直接実行して結果を返す（認証不要）"""
    from services.market_data import _calc_record, DEFAULT_UNIVERSE
    meta = DEFAULT_UNIVERSE[0]  # トヨタ
    try:
        result = _calc_record(meta)
        return {"meta": meta, "result": result}
    except Exception as e:
        return {"meta": meta, "result": None, "error": str(e), "trace": traceback.format_exc()}


@router.get("/debug3")
def debug3():
    """フィルタなしで最初の3銘柄を取得して返す（認証不要）"""
    from services.market_data import _calc_record, DEFAULT_UNIVERSE
    from concurrent.futures import ThreadPoolExecutor
    results = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        for r in ex.map(_calc_record, DEFAULT_UNIVERSE[:3]):
            results.append(r)
    return {"results": results}
