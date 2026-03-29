"""
Supabase クライアントの初期化（サービスロールキーで管理操作用）
"""

import os
from supabase import create_client, Client

_client: Client | None = None


def get_supabase() -> Client:
    """シングルトンで Supabase クライアントを返す"""
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]  # サービスロールキー（バックエンドのみ使用）
        _client = create_client(url, key)
    return _client


def verify_token(token: str) -> dict:
    """
    JWT を検証してユーザー情報を返す。
    無効なトークンの場合は例外を raise する。
    """
    sb = get_supabase()
    response = sb.auth.get_user(token)
    if not response or not response.user:
        raise ValueError("Invalid token")
    return {"id": response.user.id, "email": response.user.email}


def get_profile(user_id: str) -> dict:
    """ユーザーのプロフィール（credits, plan, language）を取得する"""
    sb = get_supabase()
    res = sb.table("profiles").select("*").eq("id", user_id).single().execute()
    return res.data


def deduct_credit(user_id: str) -> int:
    """
    クレジットを1消費する。残高0の場合は ValueError を raise する。
    返り値: 消費後の残高
    """
    sb = get_supabase()
    profile = get_profile(user_id)

    if profile["plan"] == "monthly":
        return -1  # 月額プランはクレジット不要

    if profile["credits"] <= 0:
        raise ValueError("Insufficient credits")

    new_credits = profile["credits"] - 1
    sb.table("profiles").update({"credits": new_credits}).eq("id", user_id).execute()
    return new_credits


def add_credits(user_id: str, amount: int) -> None:
    """クレジットを加算する（Stripe Webhook から呼び出す）"""
    sb = get_supabase()
    profile = get_profile(user_id)
    new_credits = profile["credits"] + amount
    sb.table("profiles").update({"credits": new_credits}).eq("id", user_id).execute()


def set_monthly_plan(user_id: str, active: bool) -> None:
    """月額プランの状態を更新する（Stripe Webhook から呼び出す）"""
    sb = get_supabase()
    plan = "monthly" if active else "free"
    sb.table("profiles").update({"plan": plan}).eq("id", user_id).execute()


def get_user_settings(user_id: str) -> dict | None:
    """ユーザー設定を取得する。未設定の場合は None を返す。"""
    sb = get_supabase()
    res = sb.table("user_settings").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None


def save_user_settings(user_id: str, settings: dict) -> None:
    """ユーザー設定を upsert する"""
    sb = get_supabase()
    sb.table("user_settings").upsert({
        "user_id": user_id,
        **settings,
        "updated_at": "now()",
    }).execute()


def save_plan_history(user_id: str, entry: dict) -> None:
    """生成した計画を履歴テーブルに保存する"""
    sb = get_supabase()
    sb.table("plan_history").insert({"user_id": user_id, **entry}).execute()


def get_plan_history(user_id: str, limit: int = 30) -> list[dict]:
    """ユーザーの生成履歴を新しい順で取得する"""
    sb = get_supabase()
    res = (
        sb.table("plan_history")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data
