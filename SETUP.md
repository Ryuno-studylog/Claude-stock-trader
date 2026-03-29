# セットアップ手順書

このファイルに「ブラウザでやること」「ターミナルでやること」をまとめています。
上から順に進めてください。

---

## STEP 1 — Supabase セットアップ

### 1-1. プロジェクト作成
1. https://supabase.com にアクセス → GitHubログイン
2. **New project** → 名前: `nightly-edge`、リージョン: `Northeast Asia (Tokyo)`
3. DB パスワードを設定（メモしておく）

### 1-2. APIキーを控える
**Settings → API** を開いて以下をメモ：

| 項目 | 使う場所 |
|---|---|
| Project URL | backend/.env と frontend/.env.local |
| `anon` `public` キー | frontend/.env.local |
| `service_role` キー ⚠️ 絶対公開NG | backend/.env のみ |

### 1-3. DBスキーマを流し込む
1. 左メニュー **SQL Editor** → **New query**
2. `supabase/migrations/001_init.sql` の中身を**まるごとコピペ**して **Run**
3. エラーが出なければOK

### 1-4. セキュリティ初期設定（必須）

**Authentication → Settings** を開いて以下を確認・変更：

| 項目 | 設定値 | 理由 |
|---|---|---|
| Enable email confirmations | **ON** | 野良アカウント作成を防ぐ |
| Minimum password length | **8以上** | 弱いパスワードを弾く |
| Site URL | `http://localhost:3000`（後で本番URLに変更） | OAuthリダイレクト先 |

**Authentication → Rate Limits** はデフォルトでON（そのままでOK）

**Database → Tables** を開いて、以下の4テーブルに `RLS enabled` のバッジがついていることを確認：
- `profiles`
- `user_settings`
- `plan_history`

ついていない場合は SQL Editor で下記を実行：
```sql
alter table public.profiles      enable row level security;
alter table public.user_settings enable row level security;
alter table public.plan_history  enable row level security;
```

**⚠️ キーの使い分け（絶対守る）**
- `anon` キー → フロントエンドのみ（RLSで保護されるので公開OK）
- `service_role` キー → バックエンドの環境変数のみ（RLSをバイパスするため絶対に公開しない）

---

### 1-5. Google OAuth を有効化（任意・後回しでもOK）

#### A. Supabase 側で Callback URL を確認
1. **Authentication → Providers → Google** を開く
2. ページ上部に表示されている **Callback URL** をコピーしておく
   - 形式: `https://xxxxxxxxxxxx.supabase.co/auth/v1/callback`

#### B. Google Cloud Console 側の設定
1. https://console.cloud.google.com にアクセス（Googleアカウントでログイン）
2. 画面上部のプロジェクト選択 → **新しいプロジェクト** → 名前: `nightly-edge` → 作成
3. 左メニュー **APIとサービス → OAuth同意画面**
   - User Type: **外部** を選択 → 作成
   - アプリ名: `Nightly Edge`、サポートメール: 自分のメール
   - **スコープは追加しない**（デフォルトのままでOK）
   - テストユーザーに自分のメールアドレスを追加 → 保存
4. 左メニュー **APIとサービス → 認証情報 → 認証情報を作成 → OAuthクライアントID**
   - アプリケーションの種類: **ウェブアプリケーション**
   - 名前: `nightly-edge-web`
   - **承認済みのリダイレクト URI** → 「URIを追加」
     - A でコピーした Supabase の Callback URL を貼る
   - 作成
5. 表示される **クライアントID** と **クライアントシークレット** をコピー

#### C. Supabase 側に貼り付ける
1. Supabase の **Authentication → Providers → Google** に戻る
2. **Client ID**（GCCのクライアントID）と **Client Secret**（GCCのクライアントシークレット）を貼る
3. **Enable Google provider** をON → Save

#### D. 本番デプロイ後に追加が必要
Vercel のURLが決まったら、GCC の「承認済みのリダイレクト URI」に本番用も追加する：
- `https://your-vercel-app.vercel.app/auth/callback`（フロントエンドのコールバック用）

---

## STEP 2 — Stripe セットアップ

### 2-1. アカウント作成・APIキーを控える
1. https://stripe.com → アカウント作成
2. ダッシュボード右上が **テストモード** になっていることを確認
3. **Developers → API keys** から控える：
   - `Publishable key`（`pk_test_...`） → frontend/.env.local
   - `Secret key`（`sk_test_...`） → backend/.env

### 2-2. 商品を2つ作成
**Products → Add product** を2回：

**商品①**
- Name: `Nightly Edge Credits`
- Pricing: One-time / $3.00 USD
- → 作成後、Price IDを控える（`price_...`）→ backend/.env の `STRIPE_CREDITS_PRICE_ID`

**商品②**
- Name: `Nightly Edge Monthly`
- Pricing: Recurring / $9.00 USD / Monthly
- → 作成後、Price IDを控える（`price_...`）→ backend/.env の `STRIPE_MONTHLY_PRICE_ID`

### 2-3. Webhook を設定（デプロイ後に実施）
※ RailwayのURLが決まってから行う

1. **Developers → Webhooks → Add endpoint**
2. Endpoint URL: `https://YOUR_RAILWAY_APP.railway.app/api/billing/webhook`
3. イベントを選択：
   - `checkout.session.completed`
   - `customer.subscription.deleted`
4. **Signing secret**（`whsec_...`）を控える → backend/.env の `STRIPE_WEBHOOK_SECRET`

---

## STEP 3 — 環境変数ファイルを作成

### backend/.env
`backend/.env.example` をコピーして `backend/.env` を作り、値を埋める：

```
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...（service_roleキー）
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...（デプロイ後に設定）
STRIPE_CREDITS_PRICE_ID=price_...
STRIPE_MONTHLY_PRICE_ID=price_...
FRONTEND_URL=http://localhost:3000
```

### frontend/.env.local
`frontend/.env.local.example` をコピーして `frontend/.env.local` を作り、値を埋める：

```
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...（anonキー）
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_STRIPE_CREDITS_PRICE_ID=price_...
NEXT_PUBLIC_STRIPE_MONTHLY_PRICE_ID=price_...
```

---

## STEP 4 — ローカル動作確認

ターミナルを2つ開いて実行：

**ターミナル①（バックエンド）**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
→ `http://localhost:8000/health` にアクセスして `{"status":"ok"}` が返ればOK

**ターミナル②（フロントエンド）**
```bash
cd frontend
npm install
npm run dev
```
→ `http://localhost:3000` にアクセスしてランディングページが表示されればOK

---

## STEP 5 — デプロイ

### 5-1. Railway（バックエンド）

#### アカウント作成・プロジェクト作成
1. https://railway.app → **Login with GitHub**
2. **New Project → Deploy from GitHub repo** → `Claude-stock-trader` を選択
3. **Add variables** と聞かれたらとりあえずスキップ（後で設定する）

#### Environment Variables を設定
1. プロジェクトが作成されたら、サービス（デプロイされたボックス）をクリック
2. 上部タブ **Variables** を開く
3. **New Variable** を1つずつ追加（Key と Value を入力して Enter）：

| Key | Value（どこから取得するか） |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic Console → API Keys |
| `SUPABASE_URL` | Supabase → Settings → API → Project URL |
| `SUPABASE_SERVICE_KEY` | Supabase → Settings → API → `service_role` キー |
| `STRIPE_SECRET_KEY` | Stripe → Developers → API keys → Secret key |
| `STRIPE_WEBHOOK_SECRET` | ⚠️ デプロイ後に設定（今は空でOK） |
| `STRIPE_CREDITS_PRICE_ID` | Stripe → Products → Credits商品 → Price ID |
| `STRIPE_MONTHLY_PRICE_ID` | Stripe → Products → Monthly商品 → Price ID |
| `FRONTEND_URL` | ⚠️ Vercelデプロイ後に設定（今は `http://localhost:3000` で仮置き） |

#### Start Command を設定
1. 上部タブ **Settings** を開く
2. **Deploy** セクション → **Start Command** に以下を入力：
   ```
   cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
3. 自動的に再デプロイが始まる

#### デプロイ確認
1. 上部タブ **Deployments** → 最新のデプロイをクリック
2. ログに `Uvicorn running on ...` が出ればOK
3. 上部タブ **Settings → Networking → Generate Domain** でURLを発行
4. 発行されたURL（例: `https://nightly-edge-production.up.railway.app`）を控える
5. このURLの末尾に `/health` をつけてブラウザで開き `{"status":"ok"}` が返ればOK

### 5-2. Vercel（フロントエンド）
1. https://vercel.com → GitHubログイン
2. **New Project → Import** → このリポジトリを選択
3. **Root Directory**: `frontend` を指定
4. **Environment Variables** に `frontend/.env.local` の中身をすべて入力
   - `NEXT_PUBLIC_API_URL` は Railway の URL に変更（例: `https://nightly-edge.railway.app`）
5. Deploy → 完了後、発行されたURLを控える（例: `https://nightly-edge.vercel.app`）

### 5-3. デプロイ後の仕上げ
- Stripe Webhook の Endpoint URL を Railway の URL に設定（STEP 2-3）
- `backend/.env` の `FRONTEND_URL` を Vercel の URL に更新して Railway を再デプロイ
- Supabase の **Authentication → URL Configuration** → Site URL を Vercel の URL に設定

---

## 完了チェックリスト

- [ ] Supabase: プロジェクト作成・APIキー取得
- [ ] Supabase: SQLスキーマ流し込み
- [ ] Stripe: アカウント作成・APIキー取得
- [ ] Stripe: 商品2つ作成・Price ID取得
- [ ] backend/.env 作成
- [ ] frontend/.env.local 作成
- [ ] ローカルでバックエンド起動確認
- [ ] ローカルでフロントエンド起動確認
- [ ] Railway デプロイ
- [ ] Vercel デプロイ
- [ ] Stripe Webhook 設定
- [ ] 本番URLで動作確認
