"""
Claude API を使った翌日売買計画生成モジュール（夜の振り返りモード）
"""

import anthropic
import pandas as pd


SYSTEM_PROMPT = """あなたは日本株の手動売買をサポートするトレードアドバイザーです。
ユーザーは個人投資家で、夜に翌日の売買計画を立て、翌朝の市場開幕前に指値・逆指値注文を手動で設定します。

## 前提
- 頻繁に売買せず、限られた予算を少しずつ動かして着実に増やすことを目標とする
- VIX が高い（25以上）火事場相場・パニック相場での新規エントリーは行わない
- 損切りラインは必ず設定し、感情での判断を避ける
- 翌朝に証券会社サイトで「指値注文」「逆指値注文」として手動入力できる具体的な価格を提示する
- **日本株の売買単位は原則100株（単元株）。推奨株数は必ず100の倍数にすること**
- 予算が1単元（現在値×100株）に届かない銘柄は候補から外すこと

## 回答フォーマット

### 📋 昨日の振り返り
（振り返りメモが提供された場合のみ）
- 良かった点・改善点を1〜2点に絞って簡潔にコメント

### 🌡️ 市場コンディション判断
- 相場のトーン（強気／弱気／中立）を一言で
- 今日の注目マクロ要因を1〜2点

### 🎯 翌日の買い候補
各候補について（最大3銘柄まで）：
- **銘柄名（コード）**
  - 指値注文価格：¥〇〇〇〇（現在値の〇%押しを狙う）
  - 株数：〇〇株（≒ ¥〇〇〇,〇〇〇 / 予算の約〇〇%）
  - 根拠：（1〜2行で簡潔に）
  - 利確ライン：¥〇〇〇〇（+〇%）で指値売り
  - 損切りライン：¥〇〇〇〇（-〇%）で逆指値売り

### ⚠️ 見送り推奨・注意事項
- 今回見送る理由があれば（ボラ高・決算前等）
- VIX が高い場合はエントリー見送りを強く推奨すること

候補がなければ「今日は見送り」と明確に伝えること。
予算の半分以上を一度に使わないように注意し、段階的なエントリーを推奨すること。"""


def _build_prompt(
    budget: int,
    watchlist: pd.DataFrame,
    holding_period: str,
    risk_tolerance: str,
    review_note: str,
    vix_info: dict,
) -> str:
    """プロンプト本文を組み立てる"""

    lines = [
        f"【本日の利用可能予算】¥{budget:,}",
        f"【保有期間の目安】{holding_period}",
        f"【リスク許容度】{risk_tolerance}",
        f"【現在のVIX】{vix_info.get('vix', '不明')}（市場レベル: {vix_info.get('level', '不明')}）",
        "",
    ]

    # 振り返りメモ
    if review_note and review_note.strip():
        lines += ["【昨日のトレード振り返りメモ】", review_note.strip(), ""]

    # スクリーニング済み銘柄リスト
    lines.append("【スクリーニング済み監視銘柄】")
    if watchlist.empty:
        lines.append("（条件に合う銘柄なし）")
    else:
        for _, row in watchlist.iterrows():
            sign = "+" if row["前日比率(%)"] >= 0 else ""
            lines.append(
                f"・{row['銘柄名']}（{row['証券コード']}）[{row['セクター']}]"
                f" 現在値¥{row['現在値']:,}"
                f" 前日比{sign}{row['前日比率(%)']:.1f}%"
                f" ATR14={row['ATR14(%)']:.1f}%"
                f" MA25乖離{'+' if row['MA25乖離(%)'] >= 0 else ''}{row['MA25乖離(%)']:.1f}%"
                f" 52週レンジ位置{row['52週レンジ位置(%)']:.0f}%"
                f" 平均出来高{row['平均出来高(千株)']:,}千株"
            )

    lines += ["", "上記をもとに、翌朝の指値・逆指値注文を具体的に提案してください。"]
    return "\n".join(lines)


def stream_trade_plan(
    budget: int,
    watchlist: pd.DataFrame,
    holding_period: str,
    risk_tolerance: str,
    review_note: str,
    vix_info: dict,
):
    """
    翌日の売買計画をストリームで生成する。
    Streamlit の st.write_stream() に渡すジェネレーターを返す。
    """
    client = anthropic.Anthropic()
    prompt = _build_prompt(budget, watchlist, holding_period, risk_tolerance, review_note, vix_info)

    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text
