"""
売買計画生成エンドポイント
POST /api/plan/generate  — SSEストリーミングで計画を返す
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.trade_advisor import stream_plan_sse
from services.supabase_client import (
    get_profile, deduct_credit, save_plan_history, count_today_usage
)

MONTHLY_DAILY_LIMIT = 3  # 月額プランの1日あたり上限
from .deps import get_current_user

router = APIRouter(prefix="/api/plan")


class PlanRequest(BaseModel):
    budget:          int
    holding_period:  str
    risk_tolerance:  str
    review_note:     str   = ""
    watchlist:       list[dict]
    vix_info:        dict
    language:        str   = "ja"


@router.post("/generate")
def generate_plan(req: PlanRequest, user: dict = Depends(get_current_user)):
    """
    Claude API で翌日売買計画を生成して SSE ストリームで返す。
    生成前にクレジット残高を確認し、完了後に履歴を保存する。
    """
    profile = get_profile(user["id"])

    # クレジット確認
    if profile["plan"] == "monthly":
        # 月額プランは1日MONTHLY_DAILY_LIMIT回まで
        if count_today_usage(user["id"]) >= MONTHLY_DAILY_LIMIT:
            raise HTTPException(status_code=429, detail="Daily limit reached")
    elif profile["credits"] <= 0:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    # クレジット消費
    try:
        deduct_credit(user["id"])
    except ValueError as e:
        raise HTTPException(status_code=402, detail=str(e))

    # 生成テキストを収集しつつ SSE 送信
    collected: list[str] = []

    def event_stream():
        for chunk in stream_plan_sse(
            budget=req.budget,
            watchlist=req.watchlist,
            holding_period=req.holding_period,
            risk_tolerance=req.risk_tolerance,
            review_note=req.review_note,
            vix_info=req.vix_info,
            language=req.language,
        ):
            collected.append(chunk)
            yield chunk

        # 生成完了後に履歴保存
        plan_text = "".join(collected).replace("data: ", "").replace("\n\n", "")
        save_plan_history(user["id"], {
            "created_at":      datetime.now(timezone.utc).isoformat(),
            "vix":             req.vix_info.get("vix"),
            "vix_level":       req.vix_info.get("level"),
            "budget":          req.budget,
            "holding_period":  req.holding_period,
            "risk_tolerance":  req.risk_tolerance,
            "review_note":     req.review_note,
            "screened_stocks": [s["name"] for s in req.watchlist],
            "plan_text":       plan_text,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
