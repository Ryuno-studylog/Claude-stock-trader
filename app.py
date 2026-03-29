"""
株式売買ブリーフィング ダッシュボード（夜の振り返り＆翌日計画モード）
"""

import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

# Windows の echo コマンドは UTF-16 で保存するため両方を試みる
_env = Path(".env")
if _env.exists():
    try:
        load_dotenv(dotenv_path=_env, encoding="utf-8")
    except UnicodeDecodeError:
        load_dotenv(dotenv_path=_env, encoding="utf-16")

from config import load_config
from market_data import get_market_safety, screen_stocks
from trade_advisor import stream_trade_plan

HISTORY_PATH = Path("plan_history.json")


def _save_history(
    vix_info, budget, holding_period, risk_tolerance,
    review_note, screened_stocks, plan_text
):
    """生成した計画を plan_history.json に追記する"""
    history = []
    if HISTORY_PATH.exists():
        try:
            history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    history.append({
        "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M"),
        "vix":             vix_info.get("vix"),
        "vix_level":       vix_info.get("level"),
        "budget":          budget,
        "holding_period":  holding_period,
        "risk_tolerance":  risk_tolerance,
        "review_note":     review_note,
        "screened_stocks": screened_stocks,
        "plan_text":       plan_text,
    })

    HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

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
        "`.env` ファイルに `ANTHROPIC_API_KEY=sk-ant-...` を記載してください。"
    )
    st.stop()

# ── 設定読み込み ──────────────────────────────────────────
cfg = load_config()
screening = cfg["screening_defaults"]
plan_def  = cfg["plan_defaults"]

# ── サイドバー：スクリーニング設定 ───────────────────────
with st.sidebar:
    st.header("🔍 スクリーニング設定")
    st.caption("詳細設定は「設定」ページから変更できます")

    min_volume = st.slider(
        "最低平均出来高（千株）",
        min_value=500, max_value=10_000,
        value=screening["min_volume_k"], step=500,
        help="流動性フィルタ。低すぎると売買しにくい銘柄が混じります",
    )
    max_atr = st.slider(
        "最大ボラティリティ ATR14（%）",
        min_value=1.0, max_value=8.0,
        value=float(screening["max_atr_pct"]), step=0.5,
        help="ATR14 ÷ 現在値。高いほど値動きが激しい",
    )
    trend = st.radio(
        "トレンドフィルタ（25日MA基準）",
        options=["どちらでも", "上昇中", "下落中"],
        index=["どちらでも", "上昇中", "下落中"].index(screening["trend"]),
    )

    st.divider()
    run_screen = st.button("📡 スクリーニング実行", type="primary", use_container_width=True)

# ── 市場安全チェック ──────────────────────────────────────
st.subheader("🌡️ 市場安全チェック")

with st.spinner("VIX 取得中..."):
    safety = get_market_safety()

level = safety["level"]
if level == "安全":
    st.success(f"**{level}**　{safety['message']}")
elif level == "注意":
    st.warning(f"**{level}**　{safety['message']}")
elif level == "警戒":
    st.warning(f"**{level}**　{safety['message']}")
elif level == "危険":
    st.error(f"**{level}**　{safety['message']}")
else:
    st.info(safety["message"])

st.divider()

# ── スクリーニング結果 ────────────────────────────────────
st.subheader("🔍 監視銘柄スクリーニング")

if "watchlist" not in st.session_state:
    st.session_state.watchlist = None

if run_screen:
    universe = cfg["stock_universe"]
    with st.spinner(f"ユニバース {len(universe)} 銘柄を取得・スクリーニング中...（30秒ほどかかります）"):
        st.session_state.watchlist = screen_stocks(
            universe=universe,
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
            "現在値":             st.column_config.NumberColumn(format="¥%d"),
            "前日比率(%)":        st.column_config.NumberColumn(format="%+.1f%%"),
            "ATR14(%)":          st.column_config.NumberColumn(format="%.2f%%"),
            "MA25乖離(%)":       st.column_config.NumberColumn(format="%+.1f%%"),
            "52週レンジ位置(%)":  st.column_config.NumberColumn(format="%.0f%%"),
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
            value=plan_def["budget"], step=10_000, format="%d",
        )
        holding_period = st.selectbox(
            "⏱️ 保有期間の目安",
            ["数日〜1週間", "数週間〜1ヶ月", "デイトレード（当日中）"],
            index=["数日〜1週間", "数週間〜1ヶ月", "デイトレード（当日中）"].index(
                plan_def["holding_period"]
            ) if plan_def["holding_period"] in ["数日〜1週間", "数週間〜1ヶ月", "デイトレード（当日中）"] else 0,
        )
    with col_r:
        options = [
            "低め（損切り -3% を基準）",
            "中程度（損切り -5% を基準）",
            "高め（損切り -8% を基準）",
        ]
        risk_tolerance = st.selectbox(
            "⚖️ リスク許容度",
            options,
            index=options.index(plan_def["risk_tolerance"]) if plan_def["risk_tolerance"] in options else 1,
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

    plan_chunks = []

    def _collecting_stream():
        """ストリームを表示しながらテキストを収集する"""
        for chunk in stream_trade_plan(
            budget=int(budget),
            watchlist=st.session_state.watchlist,
            holding_period=holding_period,
            risk_tolerance=risk_tolerance,
            review_note=review_note,
            vix_info=safety,
        ):
            plan_chunks.append(chunk)
            yield chunk

    st.write_stream(_collecting_stream())

    # 生成履歴に保存
    plan_text = "".join(plan_chunks)
    _save_history(
        vix_info=safety,
        budget=int(budget),
        holding_period=holding_period,
        risk_tolerance=risk_tolerance,
        review_note=review_note,
        screened_stocks=st.session_state.watchlist["銘柄名"].tolist(),
        plan_text=plan_text,
    )
