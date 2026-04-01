#!/usr/bin/env python3
"""
週次ツイート生成スクリプト
毎週月曜に7本分のツイート候補を生成し、scripts/output/ に保存する。

実行方法:
  python scripts/generate_tweets.py

GitHub Actions から自動実行するか、ローカルで手動実行して
生成されたMarkdownを確認・推敲してからXに投稿する。
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Windows での文字化け対策
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ローカル実行時は backend/.env を自動読み込み
_env_path = Path(__file__).parent.parent / "backend" / ".env"
if _env_path.exists() and not os.environ.get("ANTHROPIC_API_KEY"):
    for line in _env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

import anthropic
import yfinance as yf

client = anthropic.Anthropic()

# ─── コンテンツプール（週番号でローテーション）───────────────────

# 説明する用語の一覧
TERMS = [
    "ATR（Average True Range：平均真の値幅）",
    "VIX（恐怖指数）",
    "MA25（25日移動平均線）",
    "損切り・ストップロス",
    "指値注文",
    "逆指値注文",
    "単元株（100株単位）",
    "52週高値・安値レンジ",
    "出来高（流動性）",
    "前日比・騰落率",
    "乖離率（移動平均線からの距離）",
    "ボラティリティ",
    "セクター分散",
    "リスク・リワード比",
    "ポジションサイズ",
    "ドルコスト平均法",
    "信用取引と現物取引の違い",
    "PER（株価収益率）",
    "決算発表前後の値動きの特徴",
    "市場の4フェーズ（上昇・横ばい・下落・回復）",
    "IPO（新規上場）とその注意点",
    "日経平均とTOPIXの違い",
]

# 初心者向けヒント一覧
TIPS = [
    "損切りラインは「入る前」に決める。含み損が膨らんでから考えると感情が邪魔をする。",
    "1回のトレードに予算の30%以上を使わない。分散が守りの基本。",
    "VIXが急上昇した日は買いを急がない。嵐が過ぎてから動く習慣が資産を守る。",
    "ATRが低い銘柄ほど損切りラインが引きやすい。初心者はまずATR2%以下から始めよう。",
    "出来高が少ない銘柄は指値が通りにくい。1日平均1000千株以上を目安にしよう。",
    "52週高値付近は高値追いになりやすい。レンジ位置80%超は慎重に。",
    "利確ラインも逆指値で事前設定すれば、朝に注文するだけで一日動かなくていい。",
    "MA25の上か下かだけでトレンドの大まかな方向がわかる。まずここから確認する習慣を。",
    "決算発表の前後は大きく動くことが多い。初心者は決算をまたぐポジションを避けるのが無難。",
    "含み損が出ても「戻るはず」と思い込まない。その思い込みが最大の敵。",
    "週に1回だけ相場を見る、というルールを作ると感情的な売買が減る。",
    "日本株は100株単位。買う前に「現在値×100」が予算内かを必ず確認しよう。",
]

# よくある失敗・落とし穴
MISTAKES = [
    "「急落したから買い時」と反射的に飛び込む。VIX30超えはパニック相場の入口かもしれない。",
    "損切りを「もう少し待てば戻る」と先延ばしにする。先延ばしが最も損失を拡大させる。",
    "出来高の少ない銘柄を指値で入れて、約定しないまま機会を逃す。",
    "1銘柄に集中投資して、その急落で大きなダメージを受ける。",
    "毎日チャートを見すぎて感情的な売買をしてしまう。ルールを決めて機械的に動く。",
    "利益が出ているうちに売らず、欲張って天井で捕まる。利確ラインは事前に決める。",
    "相場全体が下落しているのに個別株の「割安感」だけで買う。市場環境を先に確認する。",
    "証券会社のアプリを開くたびにランキングを見て、知らない銘柄を衝動買いする。",
    "SNSで話題の銘柄を確認せずに飛びつく。話題になったころには高値圏のことが多い。",
]

# 日本株の豆知識
FACTS = [
    "東証プライムには約1,700社が上場。でも個人投資家が手を出せる流動性の高い銘柄は上位数百社が現実的。",
    "日本株の取引時間は前場9:00〜11:30、後場12:30〜15:30。昼休みがある主要取引所は世界的に珍しい。",
    "単元株制度：日本株は原則100株単位。トヨタ(7203)なら100株 ≒ 35万円〜が最低購入額になる。",
    "東証の1日あたり売買代金は約4〜5兆円。世界でも有数の市場規模を誇る。",
    "日経平均は225銘柄の「株価平均」。TOPIXは全上場株の「時価総額加重平均」。性質が根本的に違う。",
    "信用取引では自分の資金の約3.3倍の取引ができるが、その分リスクも3.3倍。初心者は現物から始めよう。",
    "日本株にはPTS（夜間取引）もあるが、流動性が極めて低い。初心者は通常の時間帯だけで十分。",
    "株主優待は日本独自の制度。年2回の優待品や割引券を目的に投資する個人投資家も多い。",
    "東証の売買単位は2018年に全社100株に統一。以前は1株・10株・1000株など銘柄によってバラバラだった。",
    "日本株は外国人投資家の売買比率が約6〜7割を占める。海外の相場動向が日本株に大きく影響する理由はここにある。",
]


# ─── 市場データ取得 ────────────────────────────────────────

def get_market_data() -> dict:
    """VIXと日経平均のデータを取得する"""
    result = {"vix": None, "vix_level": "不明", "nikkei_close": None, "nikkei_change": None}
    try:
        vix_hist = yf.Ticker("^VIX").history(period="2d")
        if not vix_hist.empty:
            vix = round(float(vix_hist["Close"].iloc[-1]), 1)
            result["vix"] = vix
            if vix < 20:
                result["vix_level"] = "安全圏"
            elif vix < 30:
                result["vix_level"] = "要注意"
            elif vix < 40:
                result["vix_level"] = "警戒圏"
            else:
                result["vix_level"] = "危険圏"
    except Exception:
        pass
    try:
        n225 = yf.Ticker("^N225").history(period="2d")
        if not n225.empty and len(n225) >= 2:
            close = float(n225["Close"].iloc[-1])
            prev  = float(n225["Close"].iloc[-2])
            result["nikkei_close"]  = round(close)
            result["nikkei_change"] = round((close - prev) / prev * 100, 2)
    except Exception:
        pass
    return result


# ─── Claudeによるツイート生成 ──────────────────────────────

def _call_claude(prompt: str) -> str:
    """Claudeにプロンプトを送り、テキストを返す"""
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def gen_market_update(market: dict) -> str:
    vix_str = f"{market['vix']}（{market['vix_level']}）" if market["vix"] else "取得不可"
    nikkei_str = (
        f"{market['nikkei_close']:,}円（前日比{'+' if market['nikkei_change'] >= 0 else ''}{market['nikkei_change']}%）"
        if market["nikkei_close"] else "取得不可"
    )
    return _call_claude(f"""
あなたは日本株投資の教育アカウントです。
今日の相場データをもとに、投資初心者が「ためになった」と感じるツイートを書いてください。

データ:
- VIX: {vix_str}
- 日経平均: {nikkei_str}

ルール:
- 140文字以内（日本語）
- VIXが何を意味するかを一言で説明しながら、今日の相場コンディションを伝える
- 初心者が「へぇ」となる視点を1つ入れる
- ハッシュタグ: #日本株 #個人投資家 を末尾に
- 絵文字を1〜2個使って読みやすく
ツイート本文のみ出力してください。""")


def gen_term_explanation(term: str) -> str:
    return _call_claude(f"""
あなたは日本株投資の教育アカウントです。
「{term}」について、株を始めたばかりの完全な初心者にも分かるツイートを書いてください。

ルール:
- 140文字以内（日本語）
- 【○○とは？】という冒頭フォーマットで始める
- 専門用語は使わず、日常の言葉で説明する
- 「なぜ知っておくと役立つか」を1行で添える
- ハッシュタグ: #株初心者 #日本株 を末尾に
- 絵文字を1〜2個（📊📚などを活用）
ツイート本文のみ出力してください。""")


def gen_beginner_tip(tip: str) -> str:
    return _call_claude(f"""
あなたは日本株投資の教育アカウントです。
以下のヒントをもとに、初心者投資家に刺さる実践的なツイートを書いてください。

ヒントの核心: {tip}

ルール:
- 140文字以内（日本語）
- 「なぜそれが大事か」の理由を1行で添える
- 上から目線にならず、「一緒に学ぼう」という共感ベースで書く
- ハッシュタグ: #投資初心者 #個人投資家 を末尾に
- 絵文字を1〜2個（💡✅など）
ツイート本文のみ出力してください。""")


def gen_common_mistake(mistake: str) -> str:
    return _call_claude(f"""
あなたは日本株投資の教育アカウントです。
初心者がやりがちな以下の失敗について、共感を呼ぶツイートを書いてください。

失敗の内容: {mistake}

ルール:
- 140文字以内（日本語）
- 「失敗あるある → 正しい考え方」の構成にする
- 責める口調ではなく「私もやりがちだった」という共感トーンで
- ハッシュタグ: #投資失敗 #個人投資家 を末尾に
- 絵文字を1〜2個（❌⚠️など）
ツイート本文のみ出力してください。""")


def gen_scenario_thinking(market: dict) -> str:
    vix = market["vix"] or 20
    level = market["vix_level"] or "要注意"
    return _call_claude(f"""
あなたは日本株投資の教育アカウントです。
「VIXが{vix}（{level}）のとき、個人投資家はどう動くべきか」を
シナリオ形式で分かりやすく説明するツイートを書いてください。

ルール:
- 140文字以内（日本語）
- 「もし○○なら→△△する」というif-then形式を使う
- 初心者が今日から実践できる具体的な行動指針を1つ含める
- ハッシュタグ: #リスク管理 #日本株 を末尾に
- 絵文字を1〜2個（🤔📌など）
ツイート本文のみ出力してください。""")


def gen_quiz() -> str:
    return _call_claude("""
あなたは日本株投資の教育アカウントです。
日本株投資の基礎知識に関するクイズツイートを1本書いてください。

ルール:
- 140文字以内（日本語）
- 三択（A/B/C）の問題形式にする（答えは次のツイートで明かすイメージで）
- 「知っていそうで知らない」という絶妙な難易度にする
- 末尾に「答えは次のツイートで！」と書く
- ハッシュタグ: #株クイズ #株初心者 を末尾に
- 絵文字を使って見やすく
ツイート本文のみ出力してください。""")


def gen_tool_spotlight() -> str:
    return _call_claude("""
あなたは日本株AIトレードサポートツール「Nightly Edge」の中の人です。
サービスの価値を自然に伝えるツイートを1本書いてください。

Nightly Edgeの特徴:
- 夜5分で翌日の売買計画をAIが生成
- VIX（恐怖指数）でパニック相場を自動検知
- ATRでボラティリティが低い安定銘柄だけをスクリーニング
- 指値・逆指値の具体的な価格と株数を提案
- 朝は証券会社で注文設定するだけ

ルール:
- 140文字以内（日本語）
- ハードセールスにならず、「こんな悩みを解決できる」というスタイルで
- URLはプロフィールリンクへ誘導する形に（URLは書かない）
- ハッシュタグ: #日本株 #個人投資家 を末尾に
- 絵文字を1〜2個（🌙など）
ツイート本文のみ出力してください。""")


def gen_market_fact(fact: str) -> str:
    return _call_claude(f"""
あなたは日本株投資の教育アカウントです。
以下の豆知識を「へぇ！」と思われる形のツイートにしてください。

豆知識: {fact}

ルール:
- 140文字以内（日本語）
- 「だから何？」という実用性・意味まで一言で触れる
- 初心者が「知らなかった！」と感じるような角度で伝える
- ハッシュタグ: #日本株 #株初心者 を末尾に
- 絵文字を1〜2個（📚💡など）
ツイート本文のみ出力してください。""")


# ─── 週次生成メイン ───────────────────────────────────────

# コンテンツタイプのラベル
TYPE_LABELS = {
    "market_update":    "📊 相場コンディション",
    "term_explanation": "📚 用語解説",
    "beginner_tip":     "💡 初心者ヒント",
    "market_fact":      "🎓 豆知識",
    "common_mistake":   "⚠️ よくある失敗",
    "scenario_thinking":"🤔 シナリオ思考",
    "quiz":             "❓ クイズ",
    "tool_spotlight":   "🌙 ツール紹介",
}


def generate_weekly_tweets() -> list[dict]:
    """1週間分（7本）のツイートを生成して返す"""

    print("📡 市場データ取得中...")
    market = get_market_data()
    print(f"   VIX: {market['vix']} / 日経: {market.get('nikkei_close', 'N/A')}")

    today = date.today()
    week_num = today.isocalendar()[1]

    # 各リストを週番号でローテーション
    term    = TERMS[week_num % len(TERMS)]
    tip     = TIPS[week_num % len(TIPS)]
    mistake = MISTAKES[week_num % len(MISTAKES)]
    fact    = FACTS[week_num % len(FACTS)]

    # 7日分のスケジュール（月〜日）
    # 4週に1回はtool_spotlightをmarket_updateの代わりに入れる
    day0_type = "tool_spotlight" if week_num % 4 == 0 else "market_update"

    schedule = [
        (day0_type,          lambda: gen_tool_spotlight() if day0_type == "tool_spotlight" else gen_market_update(market)),
        ("term_explanation",  lambda: gen_term_explanation(term)),
        ("beginner_tip",      lambda: gen_beginner_tip(tip)),
        ("market_fact",       lambda: gen_market_fact(fact)),
        ("common_mistake",    lambda: gen_common_mistake(mistake)),
        ("scenario_thinking", lambda: gen_scenario_thinking(market)),
        ("quiz",              lambda: gen_quiz()),
    ]

    base_monday = today - timedelta(days=today.weekday())
    day_names = ["月", "火", "水", "木", "金", "土", "日"]

    tweets = []
    for i, (ctype, gen_fn) in enumerate(schedule):
        post_date = base_monday + timedelta(days=i)
        label = TYPE_LABELS.get(ctype, ctype)
        print(f"  [{i+1}/7] {label} ({post_date.strftime('%m/%d')}) 生成中...")
        text = gen_fn()
        tweets.append({
            "date":  post_date.strftime("%Y-%m-%d"),
            "day":   day_names[i],
            "type":  ctype,
            "label": label,
            "text":  text,
            "chars": len(text),
        })

    return tweets


def save_as_markdown(tweets: list[dict]) -> Path:
    """ツイートをMarkdownファイルに保存する"""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    week_start = tweets[0]["date"]
    out_path = output_dir / f"tweets_{week_start}.md"

    lines = [
        f"# ツイート候補 {week_start} 週",
        "",
        "> **投稿前に確認してください**: 事実に誤りがあれば修正してから投稿してください。",
        "> 文字数が140字を超えている場合は短くしてください。",
        "",
    ]

    for t in tweets:
        over = " ⚠️ 140字超" if t["chars"] > 140 else ""
        lines += [
            "---",
            f"## {t['day']}曜日 {t['date']}｜{t['label']}",
            "",
            "```",
            t["text"],
            "```",
            "",
            f"文字数: **{t['chars']}字**{over}",
            "",
        ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ─── エントリーポイント ────────────────────────────────────

if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY が設定されていません")
        sys.exit(1)

    print("🐦 週次ツイート生成を開始します...\n")
    tweets = generate_weekly_tweets()

    print("\n💾 Markdownに保存中...")
    path = save_as_markdown(tweets)
    print(f"✅ 完了 → {path}\n")

    print("=" * 50)
    for t in tweets:
        print(f"\n【{t['day']}】{t['date']} ｜ {t['label']}（{t['chars']}字）")
        print(t["text"])
    print("=" * 50)
