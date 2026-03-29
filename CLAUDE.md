# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイドラインを提供します。

## プロジェクト概要

株式・暗号資産の取引ダッシュボードを構築するプロジェクト。Claude AI を活用した分析・意思決定支援を目的とする。

- **メイン言語**: Python
- **対象資産**: 株式・暗号資産

## 開発規約

- **コミットメッセージ**: 日本語で記述する
- **コードコメント**: 日本語で記述する

## コマンド

```bash
# 依存ライブラリのインストール
pip install -r requirements.txt

# ダッシュボードの起動
streamlit run app.py
```

## アーキテクチャ

```
app.py            # Streamlit UI（市場概況・ウォッチリスト・AI売買計画フォーム）
market_data.py    # 市場概況・ウォッチリストのデータ取得（現在はダミー）
trade_advisor.py  # Claude API を使った売買計画のストリーム生成
```

**データフロー:**
```
market_data.py
  get_market_overview() → dict（指数・為替）
  get_watchlist()       → DataFrame（監視銘柄）
         ↓
trade_advisor.py
  stream_trade_plan(budget, overview, watchlist, ...) → ジェネレーター
         ↓
app.py  st.write_stream() でリアルタイム表示
```

**実データ連携時の差し替えポイント:**
- `market_data.py` の各関数を証券 API（SBI・楽天証券 API、yfinance 等）に差し替える
- `trade_advisor.py` の `SYSTEM_PROMPT` や `_build_prompt()` でプロンプトをチューニングする

**環境変数:**
- `ANTHROPIC_API_KEY` — Claude API キー（必須）
