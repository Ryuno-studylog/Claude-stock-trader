"""
ユーザー設定・プロフィール関連エンドポイント
GET  /api/user/profile   — プロフィール取得（credits, plan, language）
GET  /api/user/settings  — カスタム設定取得
PUT  /api/user/settings  — カスタム設定保存
GET  /api/user/history   — 生成履歴取得
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.supabase_client import (
    get_profile, get_user_settings, save_user_settings, get_plan_history
)
from .deps import get_current_user

router = APIRouter(prefix="/api/user")


@router.get("/profile")
def profile(user: dict = Depends(get_current_user)):
    return get_profile(user["id"])


@router.get("/settings")
def settings(user: dict = Depends(get_current_user)):
    return get_user_settings(user["id"]) or {}


class SettingsPayload(BaseModel):
    stock_universe:     list[dict] | None = None
    screening_defaults: dict       | None = None
    plan_defaults:      dict       | None = None


@router.put("/settings")
def update_settings(payload: SettingsPayload, user: dict = Depends(get_current_user)):
    save_user_settings(user["id"], payload.model_dump(exclude_none=True))
    return {"ok": True}


@router.get("/history")
def history(user: dict = Depends(get_current_user)):
    return get_plan_history(user["id"])
