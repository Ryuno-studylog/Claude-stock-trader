# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイドラインを提供します。

---

## プロダクト概要

**Nightly Edge** — 日本株特化のAI売買計画Webアプリ。
夜に翌日の指値/逆指値注文をAIが提案し、朝の注文設定を最小化する。

- **ターゲット**: 日本株の手動トレーダー（初心者〜中級者）。日本語圏 + 日本市場に興味を持つ海外投資家
- **利用シーン**: 夜に5分で翌日計画を立て、朝は証券会社で注文設定だけする
- **差別化**: シンプルUI・VIX連動の火事場相場検知・ATRベースのスクリーニング
- **提供形式**: Webアプリ（ブラウザで完結、環境構築不要）
- **対応言語**: 日本語 / English

---

## ビジネスモデル

### 料金プラン

| プラン | 価格 | 内容 |
|---|---|---|
| Free | 無料 | 3回まで（メールアドレス登録のみ） |
| Credits | **$1 / 5回** | 都度買い切り（$0.20/回） |
| Monthly | **$3/月** | 無制限 |

- API実費 約$0.01/回（Haiku）。Stripe手数料込み原価率≈38%（Credits）
- Stripe で国際決済対応（USD建て、カード・Apple Pay等）
- 日本ユーザーは円換算表示を併記

### 収益シミュレーション
- MAU 200人 × 月額$3 = **$600/月**
- MAU 500人 × 月額$3 = **$1,500/月**

---

## ロードマップ

### ✅ Done — ローカルMVP
- Streamlit + yfinance でローカル動作
- VIX安全チェック・ATRスクリーニング
- Claude API（Haiku）による翌日計画生成
- 設定UI・履歴保存

---

### 🚧 Phase 1 — Webアプリ基盤（3〜4週間）

**目標**: ブラウザで開いてすぐ使えるWebアプリをデプロイする

#### Week 1-2: バックエンド
- [ ] FastAPI プロジェクト構成（`backend/`）
- [ ] `POST /api/screen` — スクリーニングエンドポイント
- [ ] `POST /api/generate-plan` — 計画生成エンドポイント（Claudeキーをサーバーに閉じ込める）
- [ ] `GET /api/safety` — VIXチェックエンドポイント
- [ ] Supabase プロジェクト作成・Auth設定（Google OAuth + メール）
- [ ] users テーブル（credits残高・language・設定）
- [ ] plan_history テーブル

#### Week 3: フロントエンド
- [ ] Next.js プロジェクト構成（`frontend/`）
- [ ] next-intl で JP/EN 対応
- [ ] 認証フロー（ログイン・サインアップ・Google OAuth）
- [ ] メイン画面（スクリーニング・VIXバナー・計画生成フォーム）
- [ ] 設定・履歴画面

#### Week 4: 課金 + デプロイ
- [ ] Stripe Checkout 統合（Credits購入・Monthly購入）
- [ ] Stripe Webhook でクレジット残高更新
- [ ] Railway（バックエンド）+ Vercel（フロントエンド）デプロイ
- [ ] カスタムドメイン設定

---

### 🔜 Phase 2 — グロース（5〜8週間目）

**目標**: 海外ユーザー獲得・LTV向上

- [ ] ランディングページ（LP）— EN/JP、デモGIF・料金・FAQ
- [ ] メール通知（前日の計画リマインダー）
- [ ] 紹介コード制度（招待で両者に1回分クレジット付与）
- [ ] 韓国語・中国語（繁体字）追加（アジア系投資家向け）
- [ ] ポートフォリオ管理（保有銘柄・損益トラッキング）
- [ ] Product Hunt ローンチ

---

### 🔮 Phase 3 — 機能拡張（3ヶ月目以降）

- [ ] バックテスト（AIの過去提案の勝率を可視化）
- [ ] 証券口座API連携（自動注文、SBI/楽天）
- [ ] カスタムスクリーニング条件の保存・共有
- [ ] コミュニティ機能（他ユーザーのウォッチリスト公開）

---

## マーケティング戦略

### ターゲット別チャネル

**日本語圏**
- **X（Twitter）** — `#日本株` `#個人投資家` タグで計画生成デモを投稿
- **note.com** — 「AIが提案した計画で実際にどうなったか」実績レポート
- **YouTube** — 1〜2分のデモ動画

**英語圏（日本株に興味ある層）**
- **Reddit** — r/JapanFinance, r/investing, r/stocks
- **Product Hunt** — Phase 2 ローンチ時
- **X（英語）** — `#JapanStocks` `#NikkeiTrading` タグ

### コンテンツ戦略
- 実際の計画生成結果（勝ち/負け含めて）を定期投稿 → 信頼構築
- 「VIX 30超のときに何を見るか」「ATRとは何か」の解説記事
- GitHubスターを維持 → 技術者コミュニティからの流入

---

## テックスタック

| レイヤー | 技術 | 理由 |
|---|---|---|
| フロントエンド | Next.js (App Router) | i18n・SEO・Vercel無料枠 |
| バックエンド | FastAPI (Python) | 既存コードを流用しやすい |
| 認証 + DB | Supabase | Auth・PostgreSQL・RLSがセット |
| 課金 | Stripe | 国際決済・サブスク・都度課金を両立 |
| AIモデル | Claude Haiku 4.5 | コスト最小・応答速度優先 |
| バックエンドホスト | Railway | FastAPIを$5/月〜でデプロイ |
| フロントホスト | Vercel | Next.jsと相性最良・無料枠あり |
| スタイリング | Tailwind CSS | 最速で整ったUI |

---

## セキュリティ方針（最優先）

- **Anthropicキーはバックエンド環境変数のみ**。フロントエンドに絶対に渡さない
- Claude API呼び出しはすべて `backend/` 経由
- ユーザー認証はSupabase Auth（パスワードはbcrypt管理）
- クレジット残高チェックはサーバーサイドで実施（クライアントを信頼しない）
- Stripe Webhookは署名検証（`stripe.webhook.construct_event`）を必ず実装
- レートリミット: IPごと＋ユーザーごとに1日上限を設定
- HTTPS必須（Vercel・RailwayはデフォルトでHTTPS）
- 依存ライブラリは `pip audit` / `npm audit` で定期チェック
- `.env` は絶対にコミットしない（`.gitignore` で管理済み）

---

## ディレクトリ構成（目標）

```
/
├── backend/                 # FastAPI
│   ├── main.py              # エントリーポイント
│   ├── routers/
│   │   ├── market.py        # /api/safety, /api/screen
│   │   └── plan.py          # /api/generate-plan
│   ├── services/
│   │   ├── market_data.py   # yfinance（現行から流用）
│   │   └── trade_advisor.py # Claude API（現行から流用）
│   └── requirements.txt
├── frontend/                # Next.js
│   ├── app/
│   │   ├── [locale]/        # i18n ルーティング
│   │   └── ...
│   ├── messages/
│   │   ├── ja.json          # 日本語テキスト
│   │   └── en.json          # 英語テキスト
│   └── package.json
├── supabase/
│   └── migrations/          # DBスキーマ
└── CLAUDE.md
```

---

## 開発規約

- **コミットメッセージ**: 日本語で記述する
- **コードコメント**: 日本語で記述する
- **APIレスポンス**: 英語（国際対応のため）
- **UIテキスト**: `messages/ja.json` と `messages/en.json` で管理（ハードコード禁止）

---

## 現在のコード（ローカルMVP）

```bash
pip install -r requirements.txt
streamlit run app.py
```

```
app.py            # Streamlit UI
config.py         # 設定の読み書き
market_data.py    # VIXチェック・スクリーニング（yfinance）
trade_advisor.py  # Claude API による計画生成
pages/1_設定.py   # 設定画面
pages/2_履歴.py   # 履歴画面
```

※ `market_data.py` と `trade_advisor.py` のロジックは `backend/services/` にそのまま移植する
