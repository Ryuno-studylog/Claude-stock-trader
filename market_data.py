"""
市場安全チェック・銘柄スクリーニング（yfinance 使用）
"""

import yfinance as yf
import pandas as pd


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
    universe: list,
    min_volume_k: int = 2000,
    max_atr_pct: float = 4.0,
    trend: str = "どちらでも",
) -> pd.DataFrame:
    """
    指定したユニバースからスクリーニング条件で絞り込む。

    Parameters
    ----------
    universe     : config["stock_universe"] の形式のリスト
    min_volume_k : 最低平均出来高（千株）。流動性フィルタ。
    max_atr_pct  : ATR14 を現在値で割った割合(%)の上限。ボラティリティフィルタ。
    trend        : "上昇中"（MA25上）/ "下落中"（MA25下）/ "どちらでも"
    """
    if not universe:
        return pd.DataFrame()

    from concurrent.futures import ThreadPoolExecutor

    def _fetch(meta):
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
            prev      = float(close.iloc[-2]) if len(close) >= 2 else current
            day_chg   = (current - prev) / prev * 100
            return {
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
            }
        except Exception:
            return None

    records = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for r in executor.map(_fetch, universe):
            if r:
                records.append(r)

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
