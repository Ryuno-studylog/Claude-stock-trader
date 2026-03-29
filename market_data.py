"""
市場安全チェック・銘柄スクリーニング（yfinance 使用）
"""

import yfinance as yf
import pandas as pd

# ── 監視ユニバース（流動性の高い主要銘柄） ──────────────────────
STOCK_UNIVERSE = [
    # 自動車
    {"証券コード": "7203", "ticker": "7203.T", "銘柄名": "トヨタ自動車",         "セクター": "自動車"},
    {"証券コード": "7267", "ticker": "7267.T", "銘柄名": "ホンダ",               "セクター": "自動車"},
    # 半導体・電子部品
    {"証券コード": "6857", "ticker": "6857.T", "銘柄名": "アドバンテスト",        "セクター": "半導体"},
    {"証券コード": "8035", "ticker": "8035.T", "銘柄名": "東京エレクトロン",      "セクター": "半導体"},
    {"証券コード": "6594", "ticker": "6594.T", "銘柄名": "日本電産（ニデック）",  "セクター": "電子部品"},
    # 電機・精密
    {"証券コード": "6758", "ticker": "6758.T", "銘柄名": "ソニーグループ",        "セクター": "電機"},
    {"証券コード": "6501", "ticker": "6501.T", "銘柄名": "日立製作所",            "セクター": "電機"},
    {"証券コード": "6702", "ticker": "6702.T", "銘柄名": "富士通",               "セクター": "IT"},
    {"証券コード": "6954", "ticker": "6954.T", "銘柄名": "ファナック",            "セクター": "精密機器"},
    # IT・通信
    {"証券コード": "9984", "ticker": "9984.T", "銘柄名": "ソフトバンクグループ",  "セクター": "IT投資"},
    {"証券コード": "9432", "ticker": "9432.T", "銘柄名": "NTT",                  "セクター": "通信"},
    {"証券コード": "9433", "ticker": "9433.T", "銘柄名": "KDDI",                 "セクター": "通信"},
    # 金融・銀行
    {"証券コード": "8306", "ticker": "8306.T", "銘柄名": "三菱UFJフィナンシャル", "セクター": "銀行"},
    {"証券コード": "8316", "ticker": "8316.T", "銘柄名": "三井住友フィナンシャル","セクター": "銀行"},
    {"証券コード": "8411", "ticker": "8411.T", "銘柄名": "みずほフィナンシャル",  "セクター": "銀行"},
    # 化学・素材
    {"証券コード": "4063", "ticker": "4063.T", "銘柄名": "信越化学工業",          "セクター": "化学"},
    {"証券コード": "4188", "ticker": "4188.T", "銘柄名": "三菱ケミカル",          "セクター": "化学"},
    # 小売・消費財
    {"証券コード": "9983", "ticker": "9983.T", "銘柄名": "ファーストリテイリング", "セクター": "小売"},
    {"証券コード": "3382", "ticker": "3382.T", "銘柄名": "セブン＆アイ",          "セクター": "小売"},
    {"証券コード": "2914", "ticker": "2914.T", "銘柄名": "JT（日本たばこ産業）",  "セクター": "食品"},
    # 医薬品
    {"証券コード": "4519", "ticker": "4519.T", "銘柄名": "中外製薬",              "セクター": "医薬品"},
    {"証券コード": "4568", "ticker": "4568.T", "銘柄名": "第一三共",              "セクター": "医薬品"},
    # エネルギー
    {"証券コード": "5020", "ticker": "5020.T", "銘柄名": "ENEOS",               "セクター": "エネルギー"},
    # 不動産
    {"証券コード": "8801", "ticker": "8801.T", "銘柄名": "三井不動産",            "セクター": "不動産"},
]


def get_market_safety() -> dict:
    """
    VIX を取得して市場の安全レベルを判定する。
    返り値: {"vix": float, "level": str, "safe": bool, "message": str}
    """
    try:
        hist = yf.Ticker("^VIX").history(period="5d")
        if hist.empty:
            return {"vix": None, "level": "不明", "safe": True, "message": "VIX 取得不可"}
        vix = round(float(hist["Close"].iloc[-1]), 1)
    except Exception:
        return {"vix": None, "level": "不明", "safe": True, "message": "VIX 取得不可"}

    if vix < 20:
        return {"vix": vix, "level": "安全", "safe": True,
                "message": f"VIX {vix} — 市場は落ち着いています。通常通り計画を立てましょう。"}
    elif vix < 30:
        return {"vix": vix, "level": "注意", "safe": True,
                "message": f"VIX {vix} — やや不安定。ATRスクリーナーを絞り気味にし、予算を抑えめに。"}
    elif vix < 40:
        return {"vix": vix, "level": "警戒", "safe": True,
                "message": f"VIX {vix} — 高ボラ相場。個別銘柄のATRを確認し、影響の少ない銘柄のみ検討してください。"}
    else:
        return {"vix": vix, "level": "危険", "safe": False,
                "message": f"VIX {vix} — 市場全体がパニック状態。新規エントリーは全銘柄控えることを推奨します。"}


def screen_stocks(
    min_volume_k: int = 2000,
    max_atr_pct: float = 4.0,
    trend: str = "どちらでも",
) -> pd.DataFrame:
    """
    ユニバースからスクリーニング条件で絞り込む。

    Parameters
    ----------
    min_volume_k : 最低平均出来高（千株）。流動性フィルタ。
    max_atr_pct  : ATR14 を現在値で割った割合(%)の上限。ボラティリティフィルタ。
    trend        : "上昇中"（MA25上）/ "下落中"（MA25下）/ "どちらでも"
    """
    tickers = [s["ticker"] for s in STOCK_UNIVERSE]

    # バッチ取得（API コールを最小化）
    raw = yf.download(
        tickers,
        period="1y",
        group_by="ticker",
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    records = []
    for meta in STOCK_UNIVERSE:
        tk = meta["ticker"]
        try:
            # MultiIndex 対応
            hist = raw[tk].dropna() if len(tickers) > 1 else raw.dropna()
            if len(hist) < 30:
                continue

            close  = hist["Close"]
            high_s = hist["High"]
            low_s  = hist["Low"]
            vol_s  = hist["Volume"]

            current   = float(close.iloc[-1])
            avg_vol_k = int(vol_s.tail(20).mean() / 1000)

            # ATR14（平均真の値幅）
            tr = pd.concat([
                high_s - low_s,
                (high_s - close.shift()).abs(),
                (low_s  - close.shift()).abs(),
            ], axis=1).max(axis=1)
            atr14_pct = float(tr.tail(14).mean()) / current * 100

            # 25日移動平均との乖離
            ma25      = float(close.tail(25).mean())
            ma25_diff = (current - ma25) / ma25 * 100

            # 52週レンジ位置（0%=年初来安値、100%=年初来高値）
            high52    = float(high_s.max())
            low52     = float(low_s.min())
            range_pos = (current - low52) / (high52 - low52) * 100 if high52 != low52 else 50.0

            # 前日比
            prev    = float(close.iloc[-2]) if len(close) >= 2 else current
            day_chg = (current - prev) / prev * 100

            records.append({
                "証券コード":         meta["証券コード"],
                "銘柄名":             meta["銘柄名"],
                "セクター":           meta["セクター"],
                "現在値":             round(current),
                "前日比率(%)":        round(day_chg, 2),
                "平均出来高(千株)":   avg_vol_k,
                "ATR14(%)":          round(atr14_pct, 2),
                "MA25乖離(%)":       round(ma25_diff, 2),
                "52週レンジ位置(%)":  round(range_pos, 1),
                "52週高値":           round(high52),
                "52週安値":           round(low52),
            })
        except Exception:
            pass

    df = pd.DataFrame(records)
    if df.empty:
        return df

    # フィルタ適用
    df = df[df["平均出来高(千株)"] >= min_volume_k]
    df = df[df["ATR14(%)"]        <= max_atr_pct]
    if trend == "上昇中":
        df = df[df["MA25乖離(%)"] > 0]
    elif trend == "下落中":
        df = df[df["MA25乖離(%)"] < 0]

    return df.sort_values("ATR14(%)").reset_index(drop=True)
