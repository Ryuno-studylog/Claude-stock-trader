"""
Stripe 課金エンドポイント
POST /api/billing/checkout  — Checkout セッション作成
POST /api/billing/webhook   — Stripe Webhook 処理
GET  /api/billing/portal    — カスタマーポータルURL取得
"""

import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from services.supabase_client import get_profile, add_credits, set_monthly_plan, get_supabase
from .deps import get_current_user

router = APIRouter(prefix="/api/billing")

# Stripeクライアント初期化（起動時に実行される）
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

CREDITS_PRICE_ID  = os.environ.get("STRIPE_CREDITS_PRICE_ID", "")   # $3 / 5回
MONTHLY_PRICE_ID  = os.environ.get("STRIPE_MONTHLY_PRICE_ID", "")   # $9/月
WEBHOOK_SECRET    = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL      = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# クレジット購入1回で付与する回数
CREDITS_PER_PURCHASE = 5


class CheckoutRequest(BaseModel):
    price_id: str   # CREDITS_PRICE_ID or MONTHLY_PRICE_ID


@router.post("/checkout")
def create_checkout(req: CheckoutRequest, user: dict = Depends(get_current_user)):
    """Stripe Checkout セッションを作成してURLを返す"""
    if req.price_id not in (CREDITS_PRICE_ID, MONTHLY_PRICE_ID):
        raise HTTPException(status_code=400, detail="Invalid price_id")

    is_subscription = req.price_id == MONTHLY_PRICE_ID
    mode = "subscription" if is_subscription else "payment"

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode=mode,
        line_items=[{"price": req.price_id, "quantity": 1}],
        success_url=f"{FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}/billing/cancel",
        metadata={"user_id": user["id"]},
    )
    return {"url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe Webhook を受け取りクレジット付与・プラン更新を行う。
    署名検証で不正リクエストを弾く。
    """
    payload   = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    etype = event["type"]
    data  = event["data"]["object"]

    if etype == "checkout.session.completed":
        user_id = data["metadata"].get("user_id")
        if not user_id:
            return {"ok": True}

        mode = data.get("mode")
        if mode == "payment":
            # クレジット購入
            add_credits(user_id, CREDITS_PER_PURCHASE)
        elif mode == "subscription":
            # 月額サブスク開始 + stripe_customer_id を保存
            set_monthly_plan(user_id, active=True)
            customer_id = data.get("customer")
            if customer_id:
                sb = get_supabase()
                sb.table("profiles").update({"stripe_customer_id": customer_id}).eq("id", user_id).execute()

    elif etype == "customer.subscription.deleted":
        # サブスクキャンセル
        sub = data
        # メタデータからuser_idを取得（checkout.sessionのメタデータはsubscriptionに引き継がれない）
        # customer IDからユーザーを特定する
        customer_id = sub.get("customer")
        if customer_id:
            sb = get_supabase()
            res = sb.table("profiles").select("id").eq("stripe_customer_id", customer_id).execute()
            if res.data:
                set_monthly_plan(res.data[0]["id"], active=False)

    return {"ok": True}


@router.get("/portal")
def customer_portal(user: dict = Depends(get_current_user)):
    """Stripe カスタマーポータルのURLを返す（サブスク管理用）"""
    sb = get_supabase()
    res = sb.table("profiles").select("stripe_customer_id").eq("id", user["id"]).single().execute()
    customer_id = res.data.get("stripe_customer_id") if res.data else None

    if not customer_id:
        raise HTTPException(status_code=404, detail="No billing account found")

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{FRONTEND_URL}/settings",
    )
    return {"url": session.url}
