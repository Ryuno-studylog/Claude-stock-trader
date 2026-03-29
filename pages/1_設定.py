"""
設定ページ：銘柄ユニバース・スクリーニングデフォルト・プランデフォルトを編集する
"""

import streamlit as st
import pandas as pd
from config import load_config, save_config

st.set_page_config(page_title="設定", page_icon="⚙️", layout="wide")
st.title("⚙️ 設定")

cfg = load_config()

# ── 銘柄ユニバース ────────────────────────────────────────
st.subheader("📋 銘柄ユニバース")
st.caption("スクリーニング対象の銘柄を管理します。行を追加・削除・編集できます。")

universe_df = pd.DataFrame(cfg["stock_universe"])

edited_universe = st.data_editor(
    universe_df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "証券コード": st.column_config.TextColumn("証券コード", width="small"),
        "ticker":    st.column_config.TextColumn("Ticker（例: 7203.T）", width="medium"),
        "銘柄名":    st.column_config.TextColumn("銘柄名", width="medium"),
        "セクター":  st.column_config.TextColumn("セクター", width="medium"),
    },
    hide_index=True,
)

st.caption("※ Ticker は yfinance の形式で入力してください（日本株は末尾に `.T`）")

st.divider()

# ── スクリーニングのデフォルト値 ──────────────────────────
st.subheader("🔍 スクリーニングのデフォルト値")
st.caption("メイン画面のサイドバーの初期値として使われます。")

col_l, col_r = st.columns(2)
with col_l:
    default_min_volume = st.number_input(
        "最低平均出来高（千株）",
        min_value=500, max_value=10_000,
        value=cfg["screening_defaults"]["min_volume_k"], step=500,
    )
    default_max_atr = st.number_input(
        "最大ボラティリティ ATR14（%）",
        min_value=1.0, max_value=8.0,
        value=float(cfg["screening_defaults"]["max_atr_pct"]), step=0.5,
    )
with col_r:
    default_trend = st.radio(
        "トレンドフィルタのデフォルト",
        options=["どちらでも", "上昇中", "下落中"],
        index=["どちらでも", "上昇中", "下落中"].index(cfg["screening_defaults"]["trend"]),
    )

st.divider()

# ── 売買計画フォームのデフォルト値 ────────────────────────
st.subheader("💰 売買計画フォームのデフォルト値")

col_l2, col_r2 = st.columns(2)
with col_l2:
    default_budget = st.number_input(
        "デフォルト予算（円）",
        min_value=10_000, max_value=5_000_000,
        value=cfg["plan_defaults"]["budget"], step=10_000, format="%d",
    )
with col_r2:
    period_options = ["数日〜1週間", "数週間〜1ヶ月", "デイトレード（当日中）"]
    default_period = st.selectbox(
        "デフォルト保有期間",
        period_options,
        index=period_options.index(cfg["plan_defaults"]["holding_period"])
        if cfg["plan_defaults"]["holding_period"] in period_options else 0,
    )
    risk_options = [
        "低め（損切り -3% を基準）",
        "中程度（損切り -5% を基準）",
        "高め（損切り -8% を基準）",
    ]
    default_risk = st.selectbox(
        "デフォルトリスク許容度",
        risk_options,
        index=risk_options.index(cfg["plan_defaults"]["risk_tolerance"])
        if cfg["plan_defaults"]["risk_tolerance"] in risk_options else 1,
    )

st.divider()

# ── 保存ボタン ────────────────────────────────────────────
if st.button("💾 設定を保存", type="primary", use_container_width=True):
    # ユニバースの空行を除去
    valid_universe = [
        row for row in edited_universe.to_dict("records")
        if row.get("ticker") and row.get("銘柄名")
    ]

    new_cfg = {
        "stock_universe": valid_universe,
        "screening_defaults": {
            "min_volume_k": int(default_min_volume),
            "max_atr_pct":  float(default_max_atr),
            "trend":        default_trend,
        },
        "plan_defaults": {
            "budget":         int(default_budget),
            "holding_period": default_period,
            "risk_tolerance": default_risk,
        },
    }

    save_config(new_cfg)
    st.success(f"設定を保存しました。ユニバース: {len(valid_universe)} 銘柄")
    st.rerun()
