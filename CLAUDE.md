# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイドラインを提供します。

---

## プロダクト概要

**AIトレードブリーフィング** — 個人投資家向けの夜間売買計画ツール。
夜に翌日の指値/逆指値注文をAIが提案し、朝の注文設定を最小化する。

- **ターゲット**: 日本株の手動トレーダー（初心者〜中級者）
- **利用シーン**: 夜に5分で翌日計画を立て、朝は注文設定だけする
- **差別化**: ローカル動作・シンプルUI・火事場相場の自動検知

---

## ビジネスモデル

### フェーズ別マネタイズ

#### Phase 1（今すぐ）— BYOK販売
**BYOK（Bring Your Own API Key）** モデル。ユーザーが自分のAnthropicキーを使う。
我々はUI・ロジックを提供し、サブスクで収益化。

| プラン | 価格 | 内容 |
|---|---|---|
| 月額サブスク | **¥480/月** | 使い放題（API代はユーザー負担） |

- API実費ゼロリスク・実装最速・すぐ売れる
- 販売チャネル: **note.com メンバーシップ** or **Gumroad**
- ダウンロード販売 + セットアップ動画付き

#### Phase 2（1〜2ヶ月後）— マネージドサービス
我々がAPIを持ち、クレジット制で提供。

| プラン | 価格 | 内容 |
|---|---|---|
| クレジット | **¥300 / 5回** | 都度買い切り（60円/回） |
| 月額 | **¥980/月** | 無制限 |

- API実費 約2円/回 → 粗利30倍
- 技術: Supabase（Auth+DB）+ Stripe + FastAPI on Railway

#### Phase 3（3ヶ月後以降）— 機能拡張
- 証券口座API連携（自動注文）
- ポートフォリオ管理
- バックテスト機能

---

## リリース計画

### Phase 1 タスク（1週間で完結）
- [ ] 設定（ユニバース・スクリーニング条件）をUIで編集 → `config.json` 保存
- [ ] 生成履歴をローカルJSONに保存（振り返りに使える）
- [ ] `README.md` + セットアップ動画 作成
- [ ] note.com メンバーシップ開設 or Gumroad 出品
- [ ] デモGIF/スクショ 作成

### Phase 2 タスク
- [ ] FastAPI バックエンドに移行
- [ ] Supabase Auth + ユーザーごと設定保存
- [ ] Stripe Checkout 統合
- [ ] Railway デプロイ
- [ ] Webフロントエンド（React or Streamlit維持）

---

## マーケティング戦略

### 主要チャネル（日本語圏）
1. **note.com** — 「AIで日本株の売買計画を自動生成してみた」系の記事で集客 → メンバーシップへ誘導
2. **X（Twitter）** — `#日本株` `#個人投資家` `#株式投資` タグで実績・デモを投稿
3. **YouTube** — 1〜2分のデモ動画（使い方 + 実際の出力）
4. **Reddit** — r/JapanFinance, r/investing での紹介

### コンテンツ戦略
- 「VIXが上がったときに何を見るべきか」
- 「ATRで銘柄を絞る理由」
- 「AIが提案した計画で実際にどうなったか」（実績ログ公開）

### グロースハック
- Phase 1はオープンソース維持 → GitHubスターで信頼構築
- ユーザーの振り返りログをアノニマイズして学習改善に活用
- 紹介コード制度（Phase 2〜）

---

## セキュリティ方針（最優先）

### Phase 1（BYOK）
- APIキーはセッションメモリのみ保持（ファイル・DBに保存しない）
- `.env` は `.gitignore` に含める（絶対にコミットしない）
- ユーザーには「自分のキーをここに貼るリスク」を明記する

### Phase 2（マネージドサービス）
- **Anthropicキーはサーバー環境変数のみ**。フロントエンドに絶対に渡さない
- Claude API呼び出しはすべてバックエンド経由
- ユーザーパスワードはSupabase Auth（bcrypt管理）
- レートリミット: IPごと + ユーザーごとに1日N回上限
- クレジット残高チェックはサーバーサイドで実施（クライアントを信頼しない）
- Stripeの署名検証（Webhook secret）を必ず実装

### 共通
- HTTPS必須（Railway/Renderはデフォルトで対応）
- 依存ライブラリは定期的に `pip audit` でチェック

---

## 開発規約

- **コミットメッセージ**: 日本語で記述する
- **コードコメント**: 日本語で記述する

---

## コマンド

```bash
# 依存ライブラリのインストール
pip install -r requirements.txt

# ダッシュボードの起動
streamlit run app.py
```

---

## アーキテクチャ（現在 / Phase 1）

```
app.py            # Streamlit UI（スクリーニング・VIXチェック・AI計画フォーム）
market_data.py    # VIX安全チェック・銘柄スクリーニング（yfinance）
trade_advisor.py  # Claude API（Haiku）による翌日指値計画のストリーム生成
```

**データフロー:**
```
market_data.py
  get_market_safety()  → dict（VIXレベル・警戒度）
  screen_stocks()      → DataFrame（スクリーニング済み銘柄）
         ↓
trade_advisor.py
  stream_trade_plan(budget, watchlist, vix_info, ...) → ジェネレーター
         ↓
app.py  st.write_stream() でリアルタイム表示
```

**Phase 2 移行時の差し替えポイント:**
- `app.py` → FastAPI + React/Streamlit（認証・課金レイヤー追加）
- `trade_advisor.py` → バックエンドエンドポイントに移動（キーをサーバーに閉じ込める）
- `market_data.py` → そのまま流用可能

**環境変数:**
- `ANTHROPIC_API_KEY` — Claude API キー（Phase 1はユーザー自身が管理）
