"""
履歴ページ：過去に生成した売買計画を振り返る
"""

import json
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="履歴", page_icon="📚", layout="wide")
st.title("📚 生成履歴")

HISTORY_PATH = Path("plan_history.json")

if not HISTORY_PATH.exists():
    st.info("まだ計画が生成されていません。メイン画面から計画を生成してください。")
    st.stop()

try:
    history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
except Exception as e:
    st.error(f"履歴の読み込みに失敗しました: {e}")
    st.stop()

if not history:
    st.info("履歴がありません。")
    st.stop()

# 新しい順に表示
for entry in reversed(history):
    ts       = entry.get("timestamp", "不明")
    vix      = entry.get("vix")
    level    = entry.get("vix_level", "")
    budget   = entry.get("budget", 0)
    period   = entry.get("holding_period", "")
    stocks   = entry.get("screened_stocks", [])
    review   = entry.get("review_note", "")
    plan     = entry.get("plan_text", "")

    vix_str = f"VIX {vix}（{level}）" if vix else "VIX 不明"

    with st.expander(f"📅 {ts}　|　{vix_str}　|　予算 ¥{budget:,}　|　{period}"):
        if stocks:
            st.caption("スクリーニング通過銘柄: " + "、".join(stocks))
        if review:
            st.markdown(f"**振り返りメモ:** {review}")
        st.markdown("---")
        st.markdown(plan)

st.divider()

# 履歴削除ボタン
if st.button("🗑️ 履歴をすべて削除", type="secondary"):
    HISTORY_PATH.unlink(missing_ok=True)
    st.success("履歴を削除しました。")
    st.rerun()
