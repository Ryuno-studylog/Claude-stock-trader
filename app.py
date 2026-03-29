"""
株式売買ブリーフィング ダッシュボード（夜の振り返り＆翌日計画モード）
"""

import os
from dotenv import load_dotenv
import streamlit as st

# Windows の echo コマンドは UTF-16 で保存するため両方を試みる
from pathlib import Path
_env = Path(".env")
if _env.exists():
    try:
        load_dotenv(dotenv_path=_env, encoding="utf-8")
    except UnicodeDecodeError:
        load_dotenv(dotenv_path=_env, encoding="utf-16")

from market_data import get_market_safety, screen_stocks
from trade_advisor import stream_trade_plan

# ── ページ設定 ────────────────────────────────────────────
st.set_page_config(
    page_title="翌日売買計画",
    page_icon="📋",
    layout="wide",
)

st.title("📋 翌日売買計画")

# ── API キー確認 ──────────────────────────────────────────
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not api_key:
    st.error(
        "ANTHROPIC_API_KEY が設定されていません。\n\n"
        "```\nset ANTHROPIC_API_KEY=sk-ant-...\n```"
    )
    st.stop()

# ── サイドバー：スクリーニング設定 ───────────────────────
with st.sidebar:
    st.header("🔍 スクリーニング設定")
    st.caption("銘柄を絞り込む条件を設定してください")

    min_volume = st.slider(
        "最低平均出来高（千株）",
        min_value=500, max_value=10_000, value=2_000, step=500,
        help="流動性フィルタ。低すぎると売買しにくい銘柄が混じります",
    )
    max_atr = st.slider(
        "最大ボラティリティ ATR14（%）",
        min_value=1.0, max_value=8.0, value=4.0, step=0.5,
        help="ATR14 ÷ 現在値。高いほど値動きが激しい。火事場相場を避けるため低めを推奨",
    )
    trend = st.radio(
        "トレンドフィルタ（25日MA基準）",
        options=["どちらでも", "上昇中", "下落中"],
        index=0,
    )

    st.divider()
    run_screen = st.button("📡 スクリーニング実行", type="primary", use_container_width=True)

# ── 市場安全チェック ──────────────────────────────────────
st.subheader("🌡️ 市場安全チェック")

with st.spinner("VIX 取得中..."):
    safety = get_market_safety()

level = safety["level"]
msg   = safety["message"]

if level == "安全":
    st.success(f"**{level}**　{msg}")
elif level == "注意":
    st.warning(f"**{level}**　{msg}")
elif level == "危険":
    st.error(f"**{level}**　{msg}\n\n新規エントリーは見送ることを強く推奨します。")
else:
    st.info(msg)

st.divider()

# ── スクリーニング結果 ────────────────────────────────────
st.subheader("🔍 監視銘柄スクリーニング")

if "watchlist" not in st.session_state:
    st.session_state.watchlist = None

if run_screen:
    with st.spinner(f"ユニバース全銘柄を取得・スクリーニング中...（30秒ほどかかります）"):
        st.session_state.watchlist = screen_stocks(
            min_volume_k=min_volume,
            max_atr_pct=max_atr,
            trend=trend,
        )

if st.session_state.watchlist is None:
    st.info("サイドバーの「スクリーニング実行」ボタンを押してください。")
elif st.session_state.watchlist.empty:
    st.warning("条件に合う銘柄がありませんでした。スクリーニング条件を緩めてみてください。")
else:
    wl = st.session_state.watchlist
    st.caption(f"{len(wl)} 銘柄が条件を通過しました（ATR低い順）")
    st.dataframe(
        wl[[
            "証券コード", "銘柄名", "セクター",
            "現在値", "前日比率(%)",
            "平均出来高(千株)", "ATR14(%)", "MA25乖離(%)", "52週レンジ位置(%)",
        ]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "現在値":          st.column_config.NumberColumn(format="¥%d"),
            "前日比率(%)":     st.column_config.NumberColumn(format="%+.1f%%"),
            "ATR14(%)":       st.column_config.NumberColumn(format="%.2f%%"),
            "MA25乖離(%)":    st.column_config.NumberColumn(format="%+.1f%%"),
            "52週レンジ位置(%)": st.column_config.NumberColumn(format="%.0f%%"),
        },
    )

st.divider()

# ── 翌日計画フォーム ──────────────────────────────────────
st.subheader("🤖 翌日の売買計画を立てる")

with st.form("plan_form"):
    review_note = st.text_area(
        "📝 昨日のトレード振り返り（任意）",
        placeholder="例：7203を3,200円で買い、3,280円で利確。損切りせず保持した銘柄がある。次回は損切りラインを先に決めてから入る。",
        height=100,
    )

    col_l, col_r = st.columns(2)
    with col_l:
        budget = st.number_input(
            "💰 本日の利用可能予算（円）",
            min_value=10_000, max_value=5_000_000,
            value=100_000, step=10_000, format="%d",
        )
        holding_period = st.selectbox(
            "⏱️ 保有期間の目安",
            ["数日〜1週間", "数週間〜1ヶ月", "デイトレード（当日中）"],
        )
    with col_r:
        risk_tolerance = st.selectbox(
            "⚖️ リスク許容度",
            [
                "低め（損切り -3% を基準）",
                "中程度（損切り -5% を基準）",
                "高め（損切り -8% を基準）",
            ],
        )

    submitted = st.form_submit_button(
        "📋 翌日計画を生成する",
        type="primary",
        use_container_width=True,
        disabled=(st.session_state.watchlist is None or st.session_state.watchlist.empty),
    )

if submitted:
    if not safety["safe"]:
        st.warning("VIX が極めて高い状態です。計画は生成しますが、AI の判断を参考にしつつ慎重に判断してください。")
    st.markdown("---")
    st.write_stream(
        stream_trade_plan(
            budget=int(budget),
            watchlist=st.session_state.watchlist,
            holding_period=holding_period,
            risk_tolerance=risk_tolerance,
            review_note=review_note,
            vix_info=safety,
        )
    )
