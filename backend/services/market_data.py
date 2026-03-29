"""
市場安全チェック・銘柄スクリーニング（yfinance 使用）
"""

import yfinance as yf
import pandas as pd

# デフォルトのユニバース（config未設定時のフォールバック）
DEFAULT_UNIVERSE = [
    {"証券コード": "7203", "ticker": "7203.T", "銘柄名": "トヨタ自動車",         "セクター": "自動車"},
    {"証券コード": "7267", "ticker": "7267.T", "銘柄名": "ホンダ",               "セクター": "自動車"},
    {"証券コード": "6857", "ticker": "6857.T", "銘柄名": "アドバンテスト",        "セクター": "半導体"},
    {"証券コード": "8035", "ticker": "8035.T", "銘柄名": "東京エレクトロン",      "セクター": "半導体"},
    {"証券コード": "6594", "ticker": "6594.T", "銘柄名": "日本電産（ニデック）",  "セクター": "電子部品"},
    {"証券コード": "6758", "ticker": "6758.T", "銘柄名": "ソニーグループ",        "セクター": "電機"},
    {"証券コード": "6501", "ticker": "6501.T", "銘柄名": "日立製作所",            "セクター": "電機"},
    {"証券コード": "6702", "ticker": "6702.T", "銘柄名": "富士通",               "セクター": "IT"},
    {"証券コード": "6954", "ticker": "6954.T", "銘柄名": "ファナック",            "セクター": "精密機器"},
    {"証券コード": "9984", "ticker": "9984.T", "銘柄名": "ソフトバンクグループ",  "セクター": "IT投資"},
    {"証券コード": "9432", "ticker": "9432.T", "銘柄名": "NTT",                  "セクター": "通信"},
    {"証券コード": "9433", "ticker": "9433.T", "銘柄名": "KDDI",                 "セクター": "通信"},
    {"証券コード": "8306", "ticker": "8306.T", "銘柄名": "三菱UFJフィナンシャル", "セクター": "銀行"},
    {"証券コード": "8316", "ticker": "8316.T", "銘柄名": "三井住友フィナンシャル","セクター": "銀行"},
    {"証券コード": "8411", "ticker": "8411.T", "銘柄名": "みずほフィナンシャル",  "セクター": "銀行"},
    {"証券コード": "4063", "ticker": "4063.T", "銘柄名": "信越化学工業",          "セクター": "化学"},
    {"証券コード": "4188", "ticker": "4188.T", "銘柄名": "三菱ケミカル",          "セクター": "化学"},
    {"証券コード": "9983", "ticker": "9983.T", "銘柄名": "ファーストリテイリング", "セクター": "小売"},
    {"証券コード": "3382", "ticker": "3382.T", "銘柄名": "セブン＆アイ",          "セクター": "小売"},
    {"証券コード": "2914", "ticker": "2914.T", "銘柄名": "JT（日本たばこ産業）",  "セクター": "食品"},
    {"証券コード": "4519", "ticker": "4519.T", "銘柄名": "中外製薬",              "セクター": "医薬品"},
    {"証券コード": "4568", "ticker": "4568.T", "銘柄名": "第一三共",              "セクター": "医薬品"},
    {"証券コード": "5020", "ticker": "5020.T", "銘柄名": "ENEOS",               "セクター": "エネルギー"},
    {"証券コード": "8801", "ticker": "8801.T", "銘柄名": "三井不動産",            "セクター": "不動産"},
]


def get_market_safety() -> dict:
    """VIX を取得して市場の安全レベルを判定する"""
    try:
        hist = yf.Ticker("^VIX").history(period="5d")
        if hist.empty:
            return {"vix": None, "level": "unknown", "safe": True, "message": "VIX unavailable"}
        vix = round(float(hist["Close"].iloc[-1]), 1)
    except Exception:
        return {"vix": None, "level": "unknown", "safe": True, "message": "VIX unavailable"}

    if vix < 20:
        return {"vix": vix, "level": "safe",    "safe": True,
                "message": f"VIX {vix} — Market is calm."}
    elif vix < 30:
        return {"vix": vix, "level": "caution", "safe": True,
                "message": f"VIX {vix} — Slightly volatile. Keep positions small."}
    elif vix < 40:
        return {"vix": vix, "level": "warning", "safe": True,
                "message": f"VIX {vix} — High volatility. Only consider low-ATR stocks."}
    else:
        return {"vix": vix, "level": "danger",  "safe": False,
                "message": f"VIX {vix} — Market panic. New entries not recommended."}


def _calc_record(meta: dict) -> dict | None:
    """1銘柄分のデータを取得して指標を計算する（並列処理用）"""
    try:
        hist = yf.Ticker(meta["ticker"]).history(period="1y", auto_adjust=True)
        if hist.empty or len(hist) < 30:
            return None

        close  = hist["Close"]
        high_s = hist["High"]
        low_s  = hist["Low"]
        vol_s  = hist["Volume"]

        current   = float(close.iloc[-1])
        avg_vol_k = int(vol_s.tail(20).mean() / 1000)

        tr = pd.concat([
            high_s - low_s,
            (high_s - close.shift()).abs(),
            (low_s  - close.shift()).abs(),
        ], axis=1).max(axis=1)
        atr14_pct = float(tr.tail(14).mean()) / current * 100

        ma25      = float(close.tail(25).mean())
        ma25_diff = (current - ma25) / ma25 * 100

        high52    = float(high_s.max())
        low52     = float(low_s.min())
        range_pos = (current - low52) / (high52 - low52) * 100 if high52 != low52 else 50.0

        prev    = float(close.iloc[-2]) if len(close) >= 2 else current
        day_chg = (current - prev) / prev * 100

        return {
            "code":       meta["証券コード"],
            "name":       meta["銘柄名"],
            "sector":     meta["セクター"],
            "price":      round(current),
            "day_change": round(day_chg, 2),
            "avg_vol_k":  avg_vol_k,
            "atr14_pct":  round(atr14_pct, 2),
            "ma25_diff":  round(ma25_diff, 2),
            "range_pos":  round(range_pos, 1),
            "high52":     round(high52),
            "low52":      round(low52),
        }
    except Exception:
        return None


def screen_stocks(
    universe: list,
    min_volume_k: int = 2000,
    max_atr_pct: float = 4.0,
    trend: str = "any",
) -> list[dict]:
    """
    ユニバースをスクリーニングして条件通過銘柄のリストを返す。
    個別取得＋並列処理で yfinance バージョン依存を回避する。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if not universe:
        return []

    records = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_calc_record, meta): meta for meta in universe}
        for future in as_completed(futures):
            result = future.result()
            if result:
                records.append(result)

    # フィルタ
    result = [r for r in records if r["avg_vol_k"] >= min_volume_k and r["atr14_pct"] <= max_atr_pct]
    if trend == "uptrend":
        result = [r for r in result if r["ma25_diff"] > 0]
    elif trend == "downtrend":
        result = [r for r in result if r["ma25_diff"] < 0]

    return sorted(result, key=lambda r: r["atr14_pct"])
