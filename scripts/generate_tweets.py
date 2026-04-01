#!/usr/bin/env python3
"""
ツイート生成スクリプト

使い方:
  python scripts/generate_tweets.py --mode weekly   # 日曜: 16本の予約投稿候補を生成
  python scripts/generate_tweets.py --mode daily    # 月〜金: 当日のリアルタイム投稿を生成
  python scripts/generate_tweets.py                 # デフォルト = weekly

出力先: scripts/output/
"""

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

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
JST = ZoneInfo("Asia/Tokyo")

# ─── コンテンツプール ────────────────────────────────────────

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
    "グロース株とバリュー株の違い",
    "配当利回りの見方",
]

TIPS = [
    "損切りラインは「入る前」に決める。含み損が膨らんでから考えると感情が邪魔をする。",
    "1回のトレードに予算の30%以上を使わない。分散が守りの基本。",
    "VIXが急上昇した日は買いを急がない。嵐が過ぎてから動く習慣が資産を守る。",
    "ATRが低い銘柄ほど損切りラインが引きやすい。初心者はATR2%以下から始めよう。",
    "出来高が少ない銘柄は指値が通りにくい。1日平均1000千株以上を目安に。",
    "52週高値付近は高値追いになりやすい。レンジ位置80%超は慎重に。",
    "利確ラインも逆指値で事前設定すれば、朝に注文するだけで一日動かなくていい。",
    "MA25の上か下かだけでトレンドの大まかな方向がわかる。まずここから確認しよう。",
    "決算発表の前後は大きく動くことが多い。初心者は決算をまたぐポジションを避けるのが無難。",
    "含み損が出ても「戻るはず」と思い込まない。その思い込みが最大の敵。",
    "週に1回だけ相場を見る、というルールを作ると感情的な売買が減る。",
    "日本株は100株単位。買う前に「現在値×100」が予算内かを必ず確認しよう。",
    "トレードノートをつけると、自分のクセや失敗パターンが見えてくる。",
    "利益よりも「損失を小さくすること」を最優先に考えると長続きする。",
]

MISTAKES = [
    "「急落したから買い時」と反射的に飛び込む。VIX30超えはパニック相場の入口かもしれない。",
    "損切りを「もう少し待てば戻る」と先延ばしにする。先延ばしが最も損失を拡大させる。",
    "出来高の少ない銘柄を指値で入れて、約定しないまま機会を逃す。",
    "1銘柄に集中投資して、その急落で大きなダメージを受ける。",
    "毎日チャートを見すぎて感情的な売買をしてしまう。",
    "利益が出ているうちに売らず、欲張って天井で捕まる。",
    "相場全体が下落しているのに個別株の「割安感」だけで買う。",
    "SNSで話題の銘柄を確認せずに飛びつく。話題になったころには高値圏のことが多い。",
    "証券会社アプリを開くたびにランキングを見て、知らない銘柄を衝動買いする。",
    "勝ったトレードのやり方は覚えているが、負けたトレードの理由を振り返らない。",
]

FACTS = [
    "東証プライムには約1,700社が上場。でも個人が手を出せる流動性の高い銘柄は上位数百社が現実的。",
    "日本株の取引時間は前場9:00〜11:30、後場12:30〜15:30。昼休みがある主要取引所は世界的に珍しい。",
    "単元株制度：日本株は原則100株単位。トヨタ(7203)なら100株≒35万円〜が最低購入額になる。",
    "東証の1日あたり売買代金は約4〜5兆円。世界でも有数の市場規模を誇る。",
    "日経平均は225銘柄の「株価平均」。TOPIXは全上場株の「時価総額加重平均」。性質が根本的に違う。",
    "信用取引では自分の資金の約3.3倍の取引ができるが、その分リスクも3.3倍。初心者は現物から。",
    "株主優待は日本独自の制度。年2回の優待品や割引券を目的に投資する個人投資家も多い。",
    "東証の売買単位は2018年に全社100株に統一。以前は1株・10株・1000株など銘柄によってバラバラだった。",
    "日本株は外国人投資家の売買比率が約6〜7割を占める。海外相場が日本株に大きく影響する理由はここ。",
    "日本の個人投資家数は約1,700万人。人口の約14%が株式投資をしている計算になる。",
    "NISA（少額投資非課税制度）で年間360万円まで非課税で投資できる。長期投資には強力な制度。",
    "東証のシステム障害は2020年10月に丸1日取引停止となった。そのリスクも知っておこう。",
]

SCENARIOS = [
    "VIXが突然20を超えたとき",
    "VIXが30を超えて警戒ゾーンに入ったとき",
    "保有株が1週間で10%下落したとき",
    "MA25を大きく下回る銘柄を見つけたとき",
    "52週高値付近まで上昇した銘柄を持っているとき",
    "相場全体は上昇しているのに自分の銘柄だけ下落しているとき",
    "決算発表の3日前を迎えたとき",
    "含み益が予想を大きく上回ったとき",
]

# ─── 市場データ ────────────────────────────────────────────

def get_market_data() -> dict:
    result = {"vix": None, "vix_level": "不明", "nikkei_close": None, "nikkei_change": None}
    try:
        h = yf.Ticker("^VIX").history(period="2d")
        if not h.empty:
            vix = round(float(h["Close"].iloc[-1]), 1)
            result["vix"] = vix
            result["vix_level"] = (
                "安全圏" if vix < 20 else
                "要注意" if vix < 30 else
                "警戒圏" if vix < 40 else "危険圏"
            )
    except Exception:
        pass
    try:
        h = yf.Ticker("^N225").history(period="2d")
        if not h.empty and len(h) >= 2:
            c = float(h["Close"].iloc[-1])
            p = float(h["Close"].iloc[-2])
            result["nikkei_close"]  = round(c)
            result["nikkei_change"] = round((c - p) / p * 100, 2)
    except Exception:
        pass
    return result

# ─── Claude 呼び出し ────────────────────────────────────────

def _claude(prompt: str) -> str:
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()

# ─── 各コンテンツタイプの生成関数 ────────────────────────────

def gen_market_update(market: dict) -> str:
    vix_str = f"{market['vix']}（{market['vix_level']}）" if market["vix"] else "取得不可"
    nikkei_str = (
        f"{market['nikkei_close']:,}円（{'+' if market['nikkei_change'] >= 0 else ''}{market['nikkei_change']}%）"
        if market["nikkei_close"] else "取得不可"
    )
    return _claude(f"""
あなたは日本株投資の教育アカウントです。今朝の相場データをもとにツイートを書いてください。
VIX: {vix_str} / 日経平均: {nikkei_str}
- 140文字以内（日本語）
- VIXの意味を一言で説明しつつ、今日の相場コンディションを初心者向けに伝える
- 「今日は〇〇な日」という一言判断を入れる
- ハッシュタグ: #日本株 #個人投資家
- 絵文字1〜2個
ツイート本文のみ出力してください。""")

def gen_term(term: str) -> str:
    return _claude(f"""
あなたは日本株投資の教育アカウントです。「{term}」を完全な初心者向けに解説するツイートを書いてください。
- 140文字以内（日本語）
- 【○○とは？】という冒頭フォーマットで始める
- 専門用語を使わず日常の言葉で説明
- 「なぜ知っておくと役立つか」を1行添える
- ハッシュタグ: #株初心者 #日本株
- 絵文字1〜2個（📊📚など）
ツイート本文のみ出力してください。""")

def gen_tip(tip: str) -> str:
    return _claude(f"""
あなたは日本株投資の教育アカウントです。以下のヒントを初心者向け実践ツイートにしてください。
ヒント: {tip}
- 140文字以内（日本語）
- 「なぜ大事か」の理由を1行添える
- 共感ベースで、上から目線にならない
- ハッシュタグ: #投資初心者 #個人投資家
- 絵文字1〜2個（💡✅など）
ツイート本文のみ出力してください。""")

def gen_mistake(mistake: str) -> str:
    return _claude(f"""
あなたは日本株投資の教育アカウントです。以下の失敗パターンをあるある共感ツイートにしてください。
失敗: {mistake}
- 140文字以内（日本語）
- 「失敗あるある → 正しい考え方」の構成
- 責める口調でなく「一緒に乗り越えよう」トーンで
- ハッシュタグ: #投資失敗 #個人投資家
- 絵文字1〜2個（❌⚠️など）
ツイート本文のみ出力してください。""")

def gen_fact(fact: str) -> str:
    return _claude(f"""
あなたは日本株投資の教育アカウントです。以下の豆知識を「へぇ！」と感じてもらえるツイートにしてください。
豆知識: {fact}
- 140文字以内（日本語）
- 「だから何？」という実用性まで一言で触れる
- ハッシュタグ: #日本株 #株初心者
- 絵文字1〜2個（📚💡など）
ツイート本文のみ出力してください。""")

def gen_scenario(market: dict, scenario_hint: str) -> str:
    vix = market["vix"] or 20
    return _claude(f"""
あなたは日本株投資の教育アカウントです。「{scenario_hint}」という状況での行動指針ツイートを書いてください。
現在のVIX: {vix}（{market.get('vix_level', '不明')}）
- 140文字以内（日本語）
- 「もし○○なら → △△する」というif-then形式
- 今日から実践できる具体的な行動指針を1つ含める
- ハッシュタグ: #リスク管理 #日本株
- 絵文字1〜2個（🤔📌など）
ツイート本文のみ出力してください。""")

def gen_quiz(week_num: int) -> str:
    return _claude(f"""
あなたは日本株投資の教育アカウントです。日本株の基礎知識クイズツイートを書いてください。（シード: {week_num}）
- 140文字以内（日本語）
- 三択（A/B/C）の問題形式
- 知っていそうで知らない絶妙な難易度
- 末尾に「答えは次のツイートで！」
- ハッシュタグ: #株クイズ #株初心者
- 絵文字で見やすく
ツイート本文のみ出力してください。""")

def gen_tool_spotlight() -> str:
    return _claude("""
あなたは日本株AIトレードサポートツール「Nightly Edge」の中の人です。サービスの価値を自然に伝えるツイートを書いてください。
Nightly Edgeの特徴: 夜5分で翌日の売買計画をAIが生成 / VIXでパニック相場を自動検知 / ATRで安定銘柄をスクリーニング / 指値・逆指値の価格と株数を提案 / 無料3回から試せる
- 140文字以内（日本語）
- ハードセールスにならず「こんな悩みを解決できる」スタイル
- URLはプロフィールへ誘導（URL本文に書かない）
- ハッシュタグ: #日本株 #個人投資家
- 絵文字1〜2個（🌙など）
ツイート本文のみ出力してください。""")

# ─── 週次バッチ生成（16本・予約投稿用）──────────────────────

def generate_weekly(base_monday: date, week_num: int, market: dict) -> list[dict]:
    """月〜日の予約投稿16本を生成する（朝の市場投稿は除く）"""

    # 2つの用語・ヒント・失敗・豆知識・シナリオをローテーション
    t1 = TERMS[(week_num * 2)     % len(TERMS)]
    t2 = TERMS[(week_num * 2 + 1) % len(TERMS)]
    ti1 = TIPS[(week_num * 2)     % len(TIPS)]
    ti2 = TIPS[(week_num * 2 + 1) % len(TIPS)]
    m1 = MISTAKES[(week_num * 2)     % len(MISTAKES)]
    m2 = MISTAKES[(week_num * 2 + 1) % len(MISTAKES)]
    f1 = FACTS[(week_num * 2)     % len(FACTS)]
    f2 = FACTS[(week_num * 2 + 1) % len(FACTS)]
    sc = SCENARIOS[week_num % len(SCENARIOS)]

    # 4週に1回 tool_spotlight を土曜昼に挿入
    sat_noon = ("tool_spotlight", lambda: gen_tool_spotlight()) if week_num % 4 == 0 else ("tip", lambda: gen_tip(ti2))

    # [day_offset, time_label, type_key, gen_fn]
    schedule = [
        # 月〜金の昼・夜（5日×2スロット = 10本）
        (0, "12:30", "term",     lambda: gen_term(t1)),
        (0, "19:30", "quiz",     lambda: gen_quiz(week_num)),
        (1, "12:30", "tip",      lambda: gen_tip(ti1)),
        (1, "19:30", "mistake",  lambda: gen_mistake(m1)),
        (2, "12:30", "fact",     lambda: gen_fact(f1)),
        (2, "19:30", "scenario", lambda: gen_scenario(market, sc)),
        (3, "12:30", "term",     lambda: gen_term(t2)),
        (3, "19:30", "tip",      lambda: gen_tip(ti2)),
        (4, "12:30", "mistake",  lambda: gen_mistake(m2)),
        (4, "19:30", "fact",     lambda: gen_fact(f2)),
        # 土（3スロット）
        (5, "07:30", "term",     lambda: gen_term(TERMS[(week_num * 2 + 2) % len(TERMS)])),
        (5, "12:30", sat_noon[0], sat_noon[1]),
        (5, "19:30", "quiz",     lambda: gen_quiz(week_num + 100)),
        # 日（3スロット）
        (6, "07:30", "fact",     lambda: gen_fact(FACTS[(week_num * 2 + 2) % len(FACTS)])),
        (6, "12:30", "scenario", lambda: gen_scenario(market, SCENARIOS[(week_num + 1) % len(SCENARIOS)])),
        (6, "19:30", "mistake",  lambda: gen_mistake(MISTAKES[(week_num + 2) % len(MISTAKES)])),
    ]

    type_labels = {
        "market_update": "📊 相場コンディション",
        "term":          "📚 用語解説",
        "tip":           "💡 初心者ヒント",
        "fact":          "🎓 豆知識",
        "mistake":       "⚠️ よくある失敗",
        "scenario":      "🤔 シナリオ思考",
        "quiz":          "❓ クイズ",
        "tool_spotlight":"🌙 ツール紹介",
    }

    day_names = ["月", "火", "水", "木", "金", "土", "日"]
    tweets = []

    for day_offset, time_str, type_key, gen_fn in schedule:
        post_date = base_monday + timedelta(days=day_offset)
        label = type_labels.get(type_key, type_key)
        scheduled_at = f"{post_date.strftime('%Y-%m-%d')} {time_str} JST"
        print(f"  [{len(tweets)+1:02d}/16] {day_names[day_offset]}曜 {time_str} | {label} 生成中...")
        text = gen_fn()
        tweets.append({
            "scheduled_at": scheduled_at,
            "day":          day_names[day_offset],
            "time":         time_str,
            "type":         type_key,
            "label":        label,
            "realtime":     False,
            "text":         text,
            "chars":        len(text),
        })

    return tweets

# ─── 日次リアルタイム生成（1本）─────────────────────────────

def generate_daily(today: date, market: dict) -> dict:
    """当日の朝投稿（リアルタイム市場コメント）を1本生成する"""
    print("  [1/1] 📊 相場コンディション 生成中...")
    text = gen_market_update(market)
    return {
        "scheduled_at": f"{today.strftime('%Y-%m-%d')} 07:30 JST",
        "day":          ["月","火","水","木","金","土","日"][today.weekday()],
        "time":         "07:30",
        "type":         "market_update",
        "label":        "📊 相場コンディション",
        "realtime":     True,
        "text":         text,
        "chars":        len(text),
    }

# ─── Markdown 保存 ────────────────────────────────────────

def save_markdown(tweets: list[dict], filename: str) -> Path:
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    out_path = output_dir / filename

    lines = [
        f"# ツイート候補｜{filename.replace('.md','')}",
        "",
        "> **投稿前に確認**: 事実誤認があれば修正してください。140字を超えている場合は短縮してください。",
        "",
    ]

    realtime_tweets  = [t for t in tweets if t["realtime"]]
    scheduled_tweets = [t for t in tweets if not t["realtime"]]

    if realtime_tweets:
        lines += ["## ⚡ リアルタイム投稿（当日の朝に手動投稿）", ""]
        for t in realtime_tweets:
            over = " ⚠️ 140字超" if t["chars"] > 140 else ""
            lines += [
                f"### {t['scheduled_at']} | {t['label']}",
                "", "```", t["text"], "```", "",
                f"文字数: **{t['chars']}字**{over}", "",
            ]

    if scheduled_tweets:
        lines += ["---", "## 📅 予約投稿（週末にまとめてスケジュール設定）", ""]
        for t in scheduled_tweets:
            over = " ⚠️ 140字超" if t["chars"] > 140 else ""
            lines += [
                f"### {t['scheduled_at']} | {t['label']}",
                "", "```", t["text"], "```", "",
                f"文字数: **{t['chars']}字**{over}", "",
            ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path

# ─── エントリーポイント ───────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["weekly", "daily"], default="weekly")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY が設定されていません")
        sys.exit(1)

    today    = datetime.now(JST).date()
    week_num = today.isocalendar()[1]
    monday   = today - timedelta(days=today.weekday())

    print(f"📡 市場データ取得中...")
    market = get_market_data()
    print(f"   VIX: {market['vix']} ({market['vix_level']}) / 日経: {market.get('nikkei_close','N/A')}\n")

    if args.mode == "daily":
        print(f"⚡ 当日リアルタイム投稿を生成します（{today}）\n")
        tweet = generate_daily(today, market)
        path = save_markdown([tweet], f"daily_{today}.md")
        print(f"\n✅ 完了 → {path}")
        print(f"\n【本日 07:30 投稿】{tweet['label']}（{tweet['chars']}字）")
        print(tweet["text"])

    else:  # weekly
        print(f"📅 週次予約投稿を生成します（{monday} 週）\n")
        tweets = generate_weekly(monday, week_num, market)
        path = save_markdown(tweets, f"weekly_{monday}.md")
        print(f"\n✅ 完了 → {path}")
        print(f"\n合計 {len(tweets)} 本（うち予約投稿 {sum(1 for t in tweets if not t['realtime'])} 本）")
        over = [t for t in tweets if t["chars"] > 140]
        if over:
            print(f"⚠️ 140字超: {len(over)} 本（要修正）")

if __name__ == "__main__":
    main()
