"""
Claude API を使った翌日売買計画生成（バックエンド版）
"""

import json
import anthropic

SYSTEM_PROMPT_JA = """あなたは日本株の手動売買をサポートするトレードアドバイザーです。
ユーザーは個人投資家で、夜に翌日の売買計画を立て、翌朝の市場開幕前に指値・逆指値注文を手動で設定します。

## 前提
- 頻繁に売買せず、限られた予算を少しずつ動かして着実に増やすことを目標とする
- VIX が高い火事場相場での新規エントリーは行わない
- 損切りラインは必ず設定する
- 翌朝に証券会社サイトで「指値注文」「逆指値注文」として手動入力できる具体的な価格を提示する

## 回答フォーマット

### 📋 昨日の振り返り
（振り返りメモが提供された場合のみ、1〜2点で簡潔にコメント）

### 🌡️ 市場コンディション判断
- 相場のトーンを一言で
- 注目マクロ要因を1〜2点

### 🎯 翌日の買い候補（最大3銘柄）
各候補：
- **銘柄名（コード）**
  - 指値注文価格：¥〇〇〇〇
  - 株数：〇〇株（≒ ¥〇〇〇,〇〇〇 / 予算の約〇〇%）
  - 根拠：（1〜2行）
  - 利確ライン：¥〇〇〇〇（+〇%）
  - 損切りライン：¥〇〇〇〇（-〇%）

### ⚠️ 注意事項
候補がなければ「今日は見送り」と明記。予算の半分以上を一度に使わないよう推奨。"""

SYSTEM_PROMPT_EN = """You are a trade advisor supporting manual Japanese stock trading.
The user is an individual investor who plans next-day trades each evening and sets limit/stop orders before market open.

## Principles
- Trade infrequently; grow a limited budget steadily
- Avoid new entries during panic/crisis markets (high VIX)
- Always set stop-loss levels
- Provide specific prices for limit orders and stop-loss orders

## Response Format

### 📋 Yesterday's Review
(Only if review notes provided — brief 1-2 point comment)

### 🌡️ Market Condition
- Overall tone in one line
- 1-2 key macro factors

### 🎯 Buy Candidates for Tomorrow (max 3 stocks)
For each:
- **Stock Name (Code)**
  - Limit order price: ¥〇〇〇〇
  - Shares: 〇〇 (≈ ¥〇〇〇,〇〇〇 / ~〇〇% of budget)
  - Rationale: (1-2 lines)
  - Take-profit: ¥〇〇〇〇 (+〇%)
  - Stop-loss: ¥〇〇〇〇 (-〇%)

### ⚠️ Notes
State clearly if no candidates today. Recommend not using more than half the budget at once."""


def _build_prompt(
    budget: int,
    watchlist: list[dict],
    holding_period: str,
    risk_tolerance: str,
    review_note: str,
    vix_info: dict,
    language: str = "ja",
) -> str:
    """プロンプト本文を組み立てる"""

    lines = [
        f"Budget: ¥{budget:,}",
        f"Holding period: {holding_period}",
        f"Risk tolerance: {risk_tolerance}",
        f"VIX: {vix_info.get('vix', 'N/A')} ({vix_info.get('level', 'unknown')})",
        "",
    ]

    if review_note and review_note.strip():
        lines += ["[Yesterday's review]", review_note.strip(), ""]

    lines.append("[Screened watchlist]")
    if not watchlist:
        lines.append("(No stocks passed screening)")
    else:
        for r in watchlist:
            sign = "+" if r["day_change"] >= 0 else ""
            lines.append(
                f"- {r['name']} ({r['code']}) [{r['sector']}]"
                f" ¥{r['price']:,}"
                f" {sign}{r['day_change']:.1f}%"
                f" ATR={r['atr14_pct']:.1f}%"
                f" MA25={'+' if r['ma25_diff'] >= 0 else ''}{r['ma25_diff']:.1f}%"
                f" Range={r['range_pos']:.0f}%"
                f" AvgVol={r['avg_vol_k']:,}k"
            )

    lines += ["", "Please propose tomorrow's limit/stop-loss order plan based on the above."]
    return "\n".join(lines)


def stream_plan_sse(
    budget: int,
    watchlist: list[dict],
    holding_period: str,
    risk_tolerance: str,
    review_note: str,
    vix_info: dict,
    language: str = "ja",
):
    """
    SSE形式（data: ...\n\n）でストリーミングするジェネレーター。
    FastAPI の StreamingResponse に渡す。
    """
    client = anthropic.Anthropic()
    prompt = _build_prompt(budget, watchlist, holding_period, risk_tolerance, review_note, vix_info, language)
    system = SYSTEM_PROMPT_JA if language == "ja" else SYSTEM_PROMPT_EN

    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield f"data: {json.dumps({'text': text})}\n\n"

    yield "data: [DONE]\n\n"
