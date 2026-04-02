#!/usr/bin/env python3
"""
ツイート生成スクリプト（個人感・成長特化版）

使い方:
  python scripts/generate_tweets.py --mode weekly   # 日曜: 16本の予約投稿候補を生成
  python scripts/generate_tweets.py --mode daily    # 月〜金: 当日のリアルタイム投稿を生成
"""

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

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

# ─── キャラクター設定（プロンプト全体に一貫して使う）─────────────
CHARACTER = """
あなたは「Nightly Edge」というAI日本株ツールを自分のために作ったエンジニア（30代）として投稿しています。

キャラクター設定:
- 感情で売買して何度も損をした経験がある（だからAIに判断を委ねるツールを作った）
- 専門家ではなく「同じ個人投資家の一人」として発信している
- 知識はあるが偉そうにしない。むしろ自分の失敗を積極的に晒す
- 歯に衣着せないが、煽りや根拠のない断言はしない
- 「損しないために知っておいてほしい」というスタンス
"""

# ─── コンテンツプール ────────────────────────────────────────

TERMS = [
    "ATR（Average True Range：平均真の値幅）",
    "VIX（恐怖指数）",
    "MA25（25日移動平均線）",
    "損切り・ストップロス",
    "指値注文と逆指値注文の違い",
    "単元株（100株単位）",
    "52週高値・安値レンジ",
    "出来高と流動性",
    "乖離率（移動平均線からの距離）",
    "ボラティリティ",
    "セクター分散",
    "リスク・リワード比",
    "ポジションサイズ",
    "ドルコスト平均法",
    "PER（株価収益率）",
    "決算発表前後の値動き",
    "日経平均とTOPIXの違い",
    "グロース株とバリュー株",
    "配当利回りの見方",
    "市場の4フェーズ",
    "IPO（新規上場）の注意点",
    "信用取引と現物取引の違い",
]

HOT_TAKES = [
    "証券会社の「ランキング機能」は初心者を殺すために存在していると思っている",
    "「急落=買い時」という考え方が初心者の口座を溶かしている",
    "損切りラインを決めずに株を買うのはシートベルトをしないで高速道路を走るのと同じ",
    "個人投資家が負ける理由の8割は知識不足じゃなくて感情だと思っている",
    "VIXを見ていない投資家は天気予報を見ずに外出するのと同じ",
    "「優待株は安全」という思い込みがかなり危ない",
    "出来高を確認しない株の買い方はギャンブルと変わらない",
    "「長期保有すれば必ず上がる」を信じて個別株を持ち続けるのは罠",
    "毎日株価をチェックする習慣が売買判断を狂わせている",
    "初心者ほど「難しそうな指標」を使いたがるが、ATRとMA25だけで十分だと思っている",
]

FAILURE_STORIES = [
    "VIXが30を超えているのに「もう底だろう」と全力買いして半月で20%溶かした話",
    "損切りラインを決めていたのに「もう少し待てば戻る」と先延ばしして結局3倍の損失になった話",
    "Twitterで話題になっていた銘柄を確認もせずに買って翌日大幅下落した話",
    "出来高が少ない銘柄を指値で買ったまま1週間放置して気づいたら約定していた話",
    "含み益が出ているときに「もっと上がるはず」と利確を我慢して最終的にマイナスで手放した話",
    "決算前にポジションを持ったまま翌日の暴落を食らった話",
    "1銘柄に集中投資して、その銘柄の業績悪化で口座残高が半分になった話",
]

ENGAGEMENT_QUESTIONS = [
    "正直に教えてください：損切りラインを決めずに株を買ったことありますか？",
    "日本株を始めたきっかけ、何ですか？",
    "含み損が出たとき、あなたはどうする？",
    "VIXという言葉、株を始める前から知ってましたか？",
    "一番痛かった失敗トレード、教えてもらえますか？（私も晒します）",
    "株の売買で「感情に負けた」経験、ある人いますか？",
    "損切りがどうしてもできない人、何が邪魔してる？",
]

MYTH_BUSTS = [
    "「急落したら買い時」というのは半分正解で半分嘘",
    "「長期保有すれば必ず上がる」はインデックスには当てはまるが個別株には当てはまらない",
    "「優待株は安定している」という誤解",
    "「有名な銘柄は安全」という思い込み",
    "「損切りすると確定損失になる」という感覚が一番の敵",
    "「チャートは当たらない」と言う人ほどチャートを読めていない",
]

SCENARIOS = [
    "VIXが突然20を超えたとき",
    "VIXが30を超えて警戒ゾーンに入ったとき",
    "保有株が1週間で10%下落したとき",
    "52週高値付近まで上昇した銘柄を持っているとき",
    "相場全体は上昇しているのに自分の銘柄だけ下落しているとき",
    "決算発表の3日前を迎えたとき",
    "含み益が予想を大きく上回ったとき",
]

FACTS = [
    "東証プライムには約1,700社が上場しているが、出来高トップ300社が売買代金の8割を占める",
    "日本株の取引時間は前場9:00〜11:30、後場12:30〜15:30。昼休みがある取引所は世界的に珍しい",
    "単元株制度：日本株は原則100株単位。トヨタ(7203)なら100株≒35万円〜が最低購入額",
    "日本株は外国人投資家の売買比率が約6〜7割を占める。米国相場が荒れると日本株も荒れる理由はここ",
    "NISAで年間360万円まで非課税で投資できる。長期投資には使わないと純粋に損",
    "日経平均は225銘柄の株価平均。TOPIXは全上場株の時価総額加重平均。同じ「日本株指数」でも全然違う",
    "株主優待は日本独自の制度。世界的には配当で還元するのが主流で、優待は日本特有の文化",
    "個人投資家数は約1,700万人。でも毎年継続して利益を出しているのは全体の2〜3割と言われている",
]

# ─── 市場データ ───────────────────────────────────────────

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

# ─── Claude呼び出し ──────────────────────────────────────

def _claude(prompt: str) -> str:
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": f"{CHARACTER}\n\n{prompt}"}],
    )
    text = msg.content[0].text.strip()
    if len(text) > 140:
        text = _trim(text)
    return text

def _trim(text: str) -> str:
    """140字超のツイートをClaudeに短縮させる"""
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": f"""以下のツイートを140文字以内に短縮してください。
意味・トーン・ハッシュタグは保ちつつ、不要な言い回しや重複表現を削ってください。
短縮後のツイート本文のみ出力してください。

{text}"""}],
    )
    return msg.content[0].text.strip()

# ─── 生成関数 ────────────────────────────────────────────

def gen_market_update(market: dict) -> str:
    vix_str = f"{market['vix']}（{market['vix_level']}）" if market["vix"] else "取得不可"
    nikkei_str = (
        f"{market['nikkei_close']:,}円（{'+' if market['nikkei_change'] >= 0 else ''}{market['nikkei_change']}%）"
        if market["nikkei_close"] else "取得不可"
    )
    return _claude(f"""
今朝の相場データをもとに、個人投資家として朝の一言ツイートを書いてください。

データ: VIX {vix_str} / 日経平均 {nikkei_str}

- 140文字以内（日本語）
- 「今朝VIX見て〇〇と感じた」という個人の感想から入る
- VIXが何を意味するかを一言で添える（知らない人向け）
- 今日どう動くべきかの個人的な判断を一言
- 数字を必ず入れる（具体性が大事）
- ハッシュタグは末尾に #日本株 の1個だけ
ツイート本文のみ出力してください。""")

def gen_hot_take(hot_take: str) -> str:
    return _claude(f"""
以下の持論を、思い切ってツイートしてください。

持論: {hot_take}

- 140文字以内（日本語）
- 断言口調でOK。ただし根拠のない煽りにならないよう1行で理由を添える
- 「〇〇だと思っている」「〇〇だと断言する」など自分の意見として書く
- 反論や共感を呼びやすい角度で書く（リプがつきやすいように）
- ハッシュタグは末尾に #日本株 の1個だけ
- 絵文字1個
ツイート本文のみ出力してください。""")

def gen_failure_story(story: str) -> str:
    return _claude(f"""
以下の失敗談を、個人の体験として赤裸々に書いてください。

失敗の内容: {story}

- 140文字以内（日本語）
- 「やらかした」「溶かした」など口語でOK
- 失敗の原因（感情・思い込み・ルール無視など）を1行で
- 同じ失敗をしないための教訓を最後に1行
- 自虐的にならず「同じミスをしてほしくない」というスタンスで
- ハッシュタグなし（素の本音感を出す）
ツイート本文のみ出力してください。""")

def gen_engagement(question: str) -> str:
    return _claude(f"""
以下の質問を、フォロワーに投げかけるツイートにしてください。

質問の核心: {question}

- 140文字以内（日本語）
- 「正直に教えてください」「ぶっちゃけ」など親しみやすい切り出しで
- 自分も同じ経験があることをにおわせる（共感しやすくする）
- リプライしやすい雰囲気にする
- ハッシュタグなし（会話として見せる）
- 絵文字1個
ツイート本文のみ出力してください。""")

def gen_myth_bust(myth: str) -> str:
    return _claude(f"""
以下のよくある思い込みを論破するツイートを書いてください。

思い込み: {myth}

- 140文字以内（日本語）
- 「〇〇は嘘」「〇〇という誤解」という挑発的な書き出しでOK
- 「なぜ間違いか」を1行で具体的に
- 正しい考え方を1行で
- 保存・リツイートされやすいよう「役立つ情報」感を出す
- ハッシュタグは末尾に #日本株 の1個だけ
ツイート本文のみ出力してください。""")

def gen_term(term: str) -> str:
    return _claude(f"""
「{term}」を初心者向けに解説するツイートを書いてください。

- 140文字以内（日本語）
- 「これ知らずに日本株やってると損する」という切り出しでOK
- 専門用語を使わず日常語で説明
- 「自分が知らなかった頃はこう思っていた→実際は〇〇」という構成でも可
- 保存されやすいよう「使える情報」感を出す
- ハッシュタグは末尾に #株初心者 の1個だけ
- 絵文字1〜2個
ツイート本文のみ出力してください。""")

def gen_scenario(market: dict, scenario_hint: str) -> str:
    vix = market["vix"] or 20
    return _claude(f"""
「{scenario_hint}」という場面での行動指針を、個人の経験として書いてください。

現在のVIX: {vix}（{market.get('vix_level','不明')}）

- 140文字以内（日本語）
- 「こういうとき自分はどうするか」という一人称で書く
- 「もし〇〇なら → 自分は△△する」というif-then形式
- 失敗した経験があれば1行でにおわせる
- ハッシュタグなし（個人の判断・行動として見せる）
- 絵文字1個
ツイート本文のみ出力してください。""")

def gen_fact(fact: str) -> str:
    return _claude(f"""
以下の豆知識を、思わず保存・RTされるツイートにしてください。

豆知識: {fact}

- 140文字以内（日本語）
- 「知らなかった人は損してる」「これ意外と知られてない」という切り出しでOK
- 「だから何？」という実用性まで1行で
- 数字・固有名詞を積極的に使う（具体性が信頼につながる）
- ハッシュタグは末尾に #株初心者 の1個だけ
- 絵文字1個
ツイート本文のみ出力してください。""")

def gen_quiz(seed: int) -> str:
    return _claude(f"""
日本株の基礎知識クイズを1問書いてください。（バリエーション番号: {seed}）

- 140文字以内（日本語）
- 三択（A/B/C）形式
- 「知ってそうで知らない」絶妙な難易度
- 正解した人が「これ周りに教えたい」と思えるテーマ
- 末尾「答えは次のツイートで！」
- ハッシュタグは末尾に #株クイズ の1個だけ
ツイート本文のみ出力してください。""")

def gen_tool_spotlight() -> str:
    return _claude("""
「Nightly Edge」というAI日本株ツールを作った経緯と価値を自然に伝えるツイートを書いてください。

背景: 感情で売買して何度も損をしたので、夜に翌日計画を立てて朝は注文設定だけする運用にした。
そのためのツールが欲しかったが存在しなかったので自分で作った。

- 140文字以内（日本語）
- 「作った」「使ってる」という一人称で
- 売り込みにならず「こういう悩みを解決したくて作った」スタイル
- 無料で試せることをさりげなく（URLはプロフィールへ誘導）
- ハッシュタグは末尾に #日本株 の1個だけ
- 絵文字1〜2個（🌙など）
ツイート本文のみ出力してください。""")

# ─── スケジュール構成 ─────────────────────────────────────

TYPE_LABELS = {
    "market_update": "📊 朝の相場一言",
    "hot_take":      "🔥 持論・ホットテイク",
    "failure_story": "😭 失敗談",
    "engagement":    "💬 質問・エンゲージメント",
    "myth_bust":     "🚫 よくある誤解を論破",
    "term":          "📚 用語解説",
    "scenario":      "🤔 シナリオ思考",
    "fact":          "🎓 豆知識",
    "quiz":          "❓ クイズ",
    "tool_spotlight":"🌙 ツール紹介",
}

def generate_weekly(base_monday: date, week_num: int, market: dict) -> list[dict]:
    """月〜日の予約投稿16本を生成（朝のリアルタイム投稿は除く）"""

    # ローテーションインデックス
    w = week_num
    t1  = TERMS[w * 2       % len(TERMS)]
    t2  = TERMS[(w*2+1)     % len(TERMS)]
    ht1 = HOT_TAKES[w       % len(HOT_TAKES)]
    ht2 = HOT_TAKES[(w+3)   % len(HOT_TAKES)]
    fs1 = FAILURE_STORIES[w % len(FAILURE_STORIES)]
    eq1 = ENGAGEMENT_QUESTIONS[w     % len(ENGAGEMENT_QUESTIONS)]
    eq2 = ENGAGEMENT_QUESTIONS[(w+2) % len(ENGAGEMENT_QUESTIONS)]
    mb1 = MYTH_BUSTS[w      % len(MYTH_BUSTS)]
    sc1 = SCENARIOS[w       % len(SCENARIOS)]
    sc2 = SCENARIOS[(w+2)   % len(SCENARIOS)]
    f1  = FACTS[w           % len(FACTS)]
    f2  = FACTS[(w+3)       % len(FACTS)]

    # 4週に1回ツール紹介を土曜昼に挿入
    sat_noon_type = "tool_spotlight" if w % 4 == 0 else "hot_take"
    sat_noon_fn   = (lambda: gen_tool_spotlight()) if w % 4 == 0 else (lambda: gen_hot_take(ht2))

    # [day_offset, time, type, fn]
    schedule = [
        # 月〜金 昼12:30
        (0, "12:30", "term",      lambda: gen_term(t1)),
        (1, "12:30", "myth_bust", lambda: gen_myth_bust(mb1)),
        (2, "12:30", "term",      lambda: gen_term(t2)),
        (3, "12:30", "fact",      lambda: gen_fact(f1)),
        (4, "12:30", "myth_bust", lambda: gen_myth_bust(MYTH_BUSTS[(w+2) % len(MYTH_BUSTS)])),
        # 月〜金 夜19:30
        (0, "19:30", "hot_take",     lambda: gen_hot_take(ht1)),
        (1, "19:30", "failure_story",lambda: gen_failure_story(fs1)),
        (2, "19:30", "engagement",   lambda: gen_engagement(eq1)),
        (3, "19:30", "quiz",         lambda: gen_quiz(w)),
        (4, "19:30", "scenario",     lambda: gen_scenario(market, sc1)),
        # 土
        (5, "07:30", "fact",          lambda: gen_fact(f2)),
        (5, "12:30", sat_noon_type,   sat_noon_fn),
        (5, "19:30", "engagement",    lambda: gen_engagement(eq2)),
        # 日
        (6, "07:30", "term",          lambda: gen_term(TERMS[(w*2+2) % len(TERMS)])),
        (6, "12:30", "scenario",      lambda: gen_scenario(market, sc2)),
        (6, "19:30", "failure_story", lambda: gen_failure_story(FAILURE_STORIES[(w+2) % len(FAILURE_STORIES)])),
    ]

    day_names = ["月","火","水","木","金","土","日"]
    tweets = []

    for day_off, time_str, type_key, gen_fn in schedule:
        post_date = base_monday + timedelta(days=day_off)
        label = TYPE_LABELS.get(type_key, type_key)
        print(f"  [{len(tweets)+1:02d}/16] {day_names[day_off]}曜 {time_str} | {label} 生成中...")
        text = gen_fn()
        tweets.append({
            "scheduled_at": f"{post_date.strftime('%Y-%m-%d')} {time_str} JST",
            "day":   day_names[day_off],
            "time":  time_str,
            "type":  type_key,
            "label": label,
            "realtime": False,
            "text":  text,
            "chars": len(text),
        })

    return sorted(tweets, key=lambda t: t["scheduled_at"])

def generate_daily(today: date, market: dict) -> dict:
    print("  [1/1] 📊 朝の相場一言 生成中...")
    text = gen_market_update(market)
    return {
        "scheduled_at": f"{today.strftime('%Y-%m-%d')} 07:30 JST",
        "day":   ["月","火","水","木","金","土","日"][today.weekday()],
        "time":  "07:30",
        "type":  "market_update",
        "label": TYPE_LABELS["market_update"],
        "realtime": True,
        "text":  text,
        "chars": len(text),
    }

# ─── Markdown保存 ────────────────────────────────────────

def save_markdown(tweets: list[dict], filename: str) -> Path:
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    out_path = output_dir / filename

    lines = [
        f"# ツイート候補｜{filename.replace('.md','')}",
        "",
        "> **投稿前に確認**: 事実誤認は修正してください。140字超は短縮してください。",
        "",
    ]

    realtime  = [t for t in tweets if t["realtime"]]
    scheduled = [t for t in tweets if not t["realtime"]]

    if realtime:
        lines += ["## ⚡ リアルタイム投稿（当日朝に手動投稿）", ""]
        for t in realtime:
            over = " ⚠️ 140字超" if t["chars"] > 140 else ""
            lines += [f"### {t['scheduled_at']} | {t['label']}",
                      "", "```", t["text"], "```", "",
                      f"文字数: **{t['chars']}字**{over}", ""]

    if scheduled:
        lines += ["---", "## 📅 予約投稿（週末にXでスケジュール設定）", ""]
        for t in scheduled:
            over = " ⚠️ 140字超" if t["chars"] > 140 else ""
            lines += [f"### {t['scheduled_at']} | {t['label']}",
                      "", "```", t["text"], "```", "",
                      f"文字数: **{t['chars']}字**{over}", ""]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path

# ─── エントリーポイント ──────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["weekly","daily"], default="weekly")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY が設定されていません")
        sys.exit(1)

    today    = datetime.now(JST).date()
    week_num = today.isocalendar()[1]
    monday   = today - timedelta(days=today.weekday())

    print("📡 市場データ取得中...")
    market = get_market_data()
    print(f"   VIX: {market['vix']} ({market['vix_level']}) / 日経: {market.get('nikkei_close','N/A')}\n")

    if args.mode == "daily":
        print(f"⚡ 当日リアルタイム投稿を生成します（{today}）\n")
        tweet = generate_daily(today, market)
        path  = save_markdown([tweet], f"daily_{today}.md")
        print(f"\n✅ 完了 → {path}")
        print(f"\n【本日 07:30 投稿】({tweet['chars']}字)")
        print(tweet["text"])
    else:
        print(f"📅 週次予約投稿を生成します（{monday} 週）\n")
        tweets = generate_weekly(monday, week_num, market)
        path   = save_markdown(tweets, f"weekly_{monday}.md")
        print(f"\n✅ 完了 → {path}")
        over = [t for t in tweets if t["chars"] > 140]
        if over:
            print(f"⚠️ 140字超: {len(over)} 本（要修正）")

if __name__ == "__main__":
    main()
