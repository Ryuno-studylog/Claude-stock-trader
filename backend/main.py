"""
Nightly Edge — FastAPI バックエンド
"""

import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import market, plan, user, billing

app = FastAPI(title="Nightly Edge API", version="1.0.0")

# CORS（フロントエンドからのアクセスを許可）
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router)
app.include_router(plan.router)
app.include_router(user.router)
app.include_router(billing.router)


@app.get("/health")
def health():
    return {"status": "ok"}
