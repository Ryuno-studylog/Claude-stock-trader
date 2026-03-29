"""
FastAPI 共通 Depends
"""

from fastapi import Header, HTTPException
from services.supabase_client import verify_token


def get_current_user(authorization: str = Header(...)) -> dict:
    """
    Authorization: Bearer <jwt> ヘッダーを検証してユーザー情報を返す。
    無効なトークンは 401 を返す。
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    try:
        return verify_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
